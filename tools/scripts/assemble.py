"""Steps 4–6: assemble an edit plan (EDL) into a finished video with FFmpeg (the "Finisher").

Usage:
  python tools/scripts/assemble.py output/<project>/<name>.edl.json [--preview]

--preview renders a fast 540p draft (for plan approval and timestamped feedback).
Without it, renders the full-quality master, two-pass loudness-normalised, then runs qc.py.
Always writes output/<project>/<name>.report.md (raw vs final length, every cut).

EDL format (JSON) — times in seconds:
{
  "project": "my-video", "name": "final",
  "format": "16:9" | "9:16" | "1:1",       # output shape
  "resolution": "1080p" | "4k",             # default 1080p
  "fps": 30, "loudness": -14,               # LUFS target (YouTube: -14)
  "segments": [                             # main track, played back to back
    {"src": "raw/my-video/a.mp4", "in": 12.3, "out": 18.9,
     "frame": "auto" | "center" | {"x": 0.5, "y": 0.4},  # crop focus when shapes differ (auto = face tracking)
     "fit": "crop" | "blur",                # crop to fill, or fit over a blurred copy
     "zooms": [{"at": 1.0, "dur": 3.0, "scale": 1.2, "x": 0.5, "y": 0.4, "ease": 0.3}],  # at = from segment start; ease 0 = punch-in
     "audio": true, "gain_db": 0, "captions": true, "note": "why this is here"}
  ],
  "overlays": [                             # drawn on top, in order (B-roll, animations, screenshots)
    {"src": "animations/my-video/title.mov", "at": 0.0, "dur": 3.0, "in": 0,
     "box": [x, y, w, h] (fractions of the frame; omit for full frame), "fit": "cover" | "contain",
     "zooms": [...], "audio": false, "gain_db": 0, "fade": 0.15, "note": "..."}
  ],
  "captions": {"font": "Inter", "size": 64, "color": "#FFFFFF", "highlight": "#FFD60A", ...} | null,
  "music": [{"src": "audio/my-video/track.mp3", "at": 0, "in": 0, "dur": 20, "gain_db": -22,
             "fade_in": 0.5, "fade_out": 1.5, "duck": true}],
  "sfx": [{"src": "audio/my-video/pop.wav", "at": 3.2, "gain_db": -14}]
}
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import captions
from common import ROOT, fmt_time, media_info, run, write_json

SIZES = {("16:9", "1080p"): (1920, 1080), ("16:9", "4k"): (3840, 2160),
         ("9:16", "1080p"): (1080, 1920), ("9:16", "4k"): (2160, 3840),
         ("1:1", "1080p"): (1080, 1080), ("1:1", "4k"): (2160, 2160)}
SR = 48000
_loud_cache: dict[str, float | None] = {}
_info_cache: dict[str, dict] = {}


def info(src: str) -> dict:
    if src not in _info_cache:
        _info_cache[src] = media_info(ROOT / src)
    return _info_cache[src]


def loudness(src: str) -> float | None:
    """Integrated loudness (LUFS) of a source file, used to match levels across clips."""
    if src not in _loud_cache:
        out = subprocess.run(["ffmpeg", "-nostats", "-i", str(ROOT / src), "-vn", "-af", "ebur128", "-f", "null", "-"],
                             capture_output=True, text=True).stderr
        m = re.findall(r"I:\s+(-?[\d.]+) LUFS", out)
        _loud_cache[src] = float(m[-1]) if m and float(m[-1]) > -70 else None
    return _loud_cache[src]


def zoom_expr(zooms: list[dict], key: str, default: float) -> str:
    """ffmpeg expression in t: smooth ramps between 1x and each zoom's scale (or focus point)."""
    if not zooms:
        return str(default)
    parts = []
    for z in zooms:
        a, d, e = float(z["at"]), float(z["dur"]), max(float(z.get("ease", 0.3)), 0.001)
        rin = f"clip((t-{a})/{e},0,1)"
        rout = f"clip(({a + d}-t)/{e},0,1)"
        env = f"(({rin})*({rin})*(3-2*({rin})))*(({rout})*({rout})*(3-2*({rout})))"
        target = float(z.get("scale", 1.15)) if key == "scale" else float(z.get(key, 0.5))
        parts.append(f"{target - default}*{env}")
    return f"({default}+" + "+".join(parts) + ")"


def frame_chain(src_w: int, src_h: int, W: int, H: int, fit: str, fx: float, fy: float, label: str) -> str:
    """Filters that turn any source shape into exactly WxH (crop around fx,fy, or fit over blur)."""
    if fit == "blur" and abs(src_w / src_h - W / H) > 0.01:
        return (f"split=2[{label}bg][{label}fg];"
                f"[{label}bg]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=40:5,eq=brightness=-0.08[{label}b];"
                f"[{label}fg]scale={W}:{H}:force_original_aspect_ratio=decrease[{label}f];"
                f"[{label}b][{label}f]overlay=(W-w)/2:(H-h)/2")
    return (f"scale={W}:{H}:force_original_aspect_ratio=increase,"
            f"crop={W}:{H}:x='(iw-{W})*{fx}':y='(ih-{H})*{fy}'")


def zoom_chain(zooms: list[dict], W: int, H: int) -> str:
    if not zooms:
        return ""
    s = zoom_expr(zooms, "scale", 1.0)
    x = zoom_expr(zooms, "x", 0.5)
    y = zoom_expr(zooms, "y", 0.5)
    return (f",scale=w='trunc({W}*{s}/2)*2':h='trunc({H}*{s}/2)*2':eval=frame:flags=bicubic,"
            f"crop={W}:{H}:x='(iw-{W})*{x}':y='(ih-{H})*{y}'")


def hdr_fix(i: dict) -> str:
    if not i.get("hdr"):
        return ""
    return ("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,"
            "zscale=t=bt709:m=bt709:r=tv,format=yuv420p,")


def render_segment(seg: dict, idx: int, W: int, H: int, fps: int, work: Path, preview: bool) -> Path:
    src = seg["src"]
    i = info(src)
    dur = float(seg["out"]) - float(seg["in"])
    if dur <= 0:
        sys.exit(f"Segment {idx}: out must be after in ({seg})")
    fit = seg.get("fit", "crop")
    frame = seg.get("frame", "auto")
    if i["kind"] == "image":
        fx, fy = (frame["x"], frame["y"]) if isinstance(frame, dict) else (0.5, 0.5)
    elif isinstance(frame, dict):
        fx, fy = frame["x"], frame["y"]
    elif frame == "auto" and abs(i["width"] / i["height"] - W / H) > 0.01:
        import reframe
        f = reframe.focus(str(ROOT / src), float(seg["in"]), float(seg["out"]))
        fx, fy = f["x"], f["y"]
        seg["_focus"] = f
    else:
        fx, fy = 0.5, 0.5
    # Convert subject position into crop offset fraction (keep subject centred where possible).
    if i["kind"] != "audio":
        sw, sh = i["width"], i["height"]
        k = max(W / sw, H / sh)
        cw, ch = sw * k, sh * k
        ox = 0.5 if cw <= W else min(max((fx * cw - W / 2) / (cw - W), 0), 1)
        oy = 0.5 if ch <= H else min(max((fy * ch - H / 2) / (ch - H), 0), 1)
    out = work / f"seg{idx:04d}.mkv"
    inp = (["-loop", "1", "-framerate", str(fps), "-t", f"{dur:.3f}", "-i", str(ROOT / src)] if i["kind"] == "image"
           else ["-ss", f"{float(seg['in']):.3f}", "-t", f"{dur:.3f}", "-i", str(ROOT / src)])
    vf = (f"[0:v]{hdr_fix(i)}fps={fps},setsar=1,{frame_chain(i['width'], i['height'], W, H, fit, ox, oy, 's')}"
          f"{zoom_chain(seg.get('zooms', []), W, H)},format=yuv420p[v]")
    gain = float(seg.get("gain_db", 0))
    if seg.get("normalize", True) and i.get("has_audio") and (lu := loudness(src)) is not None:
        gain += max(min(-16 - lu, 15), -15)  # bring every clip's dialogue to the same level
    use_audio = seg.get("audio", True) and i.get("has_audio")
    if use_audio:
        af = (f"[0:a]aresample={SR},aformat=channel_layouts=stereo,volume={gain}dB,"
              f"apad,atrim=0:{dur:.3f},afade=t=in:d=0.015,afade=t=out:st={max(dur - 0.015, 0):.3f}:d=0.015[a]")
    else:
        af = f"anullsrc=r={SR}:cl=stereo,atrim=0:{dur:.3f}[a]"
    enc = (["-c:v", "libx264", "-preset", "ultrafast", "-crf", "28"] if preview
           else ["-c:v", "libx264", "-preset", "medium", "-crf", "14"])
    run(["ffmpeg", "-v", "error", "-y", *inp, "-filter_complex", f"{vf};{af}", "-map", "[v]", "-map", "[a]",
         "-t", f"{dur:.3f}", "-r", str(fps), *enc, "-pix_fmt", "yuv420p", "-c:a", "pcm_s16le", str(out)])
    return out


def overlay_inputs_and_filters(edl: dict, W: int, H: int, fps: int, first_input: int):
    args, vf, aud = [], [], []
    last = "[base]"
    for k, ov in enumerate(edl.get("overlays", [])):
        n = first_input + k
        src = ov["src"]
        i = info(src)
        at, src_in = float(ov["at"]), float(ov.get("in", 0))
        dur = float(ov.get("dur") or (i["duration"] - src_in))
        if i["kind"] == "image":
            args += ["-loop", "1", "-framerate", str(fps), "-t", f"{dur:.3f}", "-i", str(ROOT / src)]
        else:
            args += ["-ss", f"{src_in:.3f}", "-t", f"{dur:.3f}", "-i", str(ROOT / src)]
        if ov.get("box"):
            bx, by, bw, bh = ov["box"]
            ow, oh = int(W * bw) // 2 * 2, int(H * bh) // 2 * 2
            px, py = int(W * bx), int(H * by)
        else:
            ow, oh, px, py = W, H, 0, 0
        if ov.get("fit", "cover") == "contain":
            shape = (f"scale={ow}:{oh}:force_original_aspect_ratio=decrease,"
                     f"pad={ow}:{oh}:(ow-iw)/2:(oh-ih)/2:color=black@0")
        else:
            fx, fy = (ov["frame"]["x"], ov["frame"]["y"]) if isinstance(ov.get("frame"), dict) else (0.5, 0.5)
            shape = f"scale={ow}:{oh}:force_original_aspect_ratio=increase,crop={ow}:{oh}:x='(iw-{ow})*{fx}':y='(ih-{oh})*{fy}'"
        fade = float(ov.get("fade", 0.15))
        fades = (f",fade=t=in:st=0:d={fade}:alpha=1,fade=t=out:st={max(dur - fade, 0):.3f}:d={fade}:alpha=1"
                 if fade > 0 else "")
        vf.append(f"[{n}:v]{hdr_fix(i)}fps={fps},setsar=1,format=yuva420p,{shape}{zoom_chain(ov.get('zooms', []), ow, oh)}"
                  f"{fades},setpts=PTS-STARTPTS+{at}/TB[ov{k}]")
        vf.append(f"{last}[ov{k}]overlay={px}:{py}:eof_action=pass:enable='between(t,{at},{at + dur})'[b{k}]")
        last = f"[b{k}]"
        if ov.get("audio") and i.get("has_audio"):
            ms = int(at * 1000)
            aud.append(f"[{n}:a]aresample={SR},aformat=channel_layouts=stereo,volume={float(ov.get('gain_db', 0))}dB,"
                       f"atrim=0:{dur:.3f},afade=t=in:d=0.05,afade=t=out:st={max(dur - 0.05, 0):.3f}:d=0.05,"
                       f"adelay={ms}|{ms}[oa{k}]")
    return args, vf, aud, last


def audio_inputs_and_filters(edl: dict, first_input: int, total: float):
    args, af, mus, sfx = [], [], [], []
    n = first_input
    for k, m in enumerate(edl.get("music", [])):
        at, src_in = float(m.get("at", 0)), float(m.get("in", 0))
        dur = float(m.get("dur") or (total - at))
        args += ["-ss", f"{src_in:.3f}", "-i", str(ROOT / m["src"])]
        fi, fo = float(m.get("fade_in", 0.5)), float(m.get("fade_out", 1.5))
        ms = int(at * 1000)
        af.append(f"[{n}:a]aresample={SR},aformat=channel_layouts=stereo,atrim=0:{dur:.3f},volume={float(m.get('gain_db', -22))}dB,"
                  f"afade=t=in:d={fi},afade=t=out:st={max(dur - fo, 0):.3f}:d={fo},adelay={ms}|{ms}[m{k}]")
        mus.append((f"[m{k}]", m.get("duck", True)))
        n += 1
    for k, s in enumerate(edl.get("sfx", [])):
        ms = int(float(s["at"]) * 1000)
        args += ["-i", str(ROOT / s["src"])]
        af.append(f"[{n}:a]aresample={SR},aformat=channel_layouts=stereo,volume={float(s.get('gain_db', -14))}dB,"
                  f"adelay={ms}|{ms}[x{k}]")
        sfx.append(f"[x{k}]")
        n += 1
    return args, af, mus, sfx


def cut_report(edl: dict, starts: list[float], total: float, dst: Path) -> None:
    inv_path = ROOT / "shotlogs" / edl["project"] / "inventory.json"
    raw_total = json.loads(inv_path.read_text())["total_raw_seconds"] if inv_path.exists() else None
    lines = [f"# Edit report: {edl['project']} / {edl.get('name', 'final')}", "",
             f"- **Raw footage:** {fmt_time(raw_total) if raw_total else 'unknown (run inventory.py)'}",
             f"- **Final video:** {fmt_time(total)}"
             + (f" ({100 * total / raw_total:.0f}% of raw)" if raw_total else ""),
             f"- **Format:** {edl.get('format', '16:9')} {edl.get('resolution', '1080p')} @ {edl.get('fps', 30)} fps", "",
             "## Timeline (final time → source)", ""]
    for seg, o in zip(edl["segments"], starts):
        d = float(seg["out"]) - float(seg["in"])
        note = f" — {seg['note']}" if seg.get("note") else ""
        foc = f" (framed on {seg['_focus']['source']})" if seg.get("_focus") else ""
        lines.append(f"- {fmt_time(o)}–{fmt_time(o + d)}: `{seg['src']}` {fmt_time(seg['in'])}–{fmt_time(seg['out'])}{foc}{note}")
    if edl.get("overlays"):
        lines += ["", "## On top (B-roll, animations, screenshots)", ""]
        for ov in edl["overlays"]:
            note = f" — {ov['note']}" if ov.get("note") else ""
            lines.append(f"- {fmt_time(float(ov['at']))}: `{ov['src']}`{note}")
    # What was cut, per source file that was used.
    lines += ["", "## What was cut", ""]
    by_src: dict[str, list[tuple[float, float]]] = {}
    for seg in edl["segments"]:
        by_src.setdefault(seg["src"], []).append((float(seg["in"]), float(seg["out"])))
    for src, kept in by_src.items():
        i = info(src)
        if i["kind"] == "image":
            continue
        kept.sort()
        gaps, pos = [], 0.0
        for a, b in kept:
            if a - pos > 0.25:
                gaps.append((pos, a))
            pos = max(pos, b)
        if i["duration"] - pos > 0.25:
            gaps.append((pos, i["duration"]))
        tpath = ROOT / "transcripts" / edl["project"] / f"{Path(src).stem}.json"
        words = json.loads(tpath.read_text())["words"] if tpath.exists() else []
        cut_total = sum(b - a for a, b in gaps)
        lines.append(f"**`{src}`** — cut {fmt_time(cut_total)} of {fmt_time(i['duration'])}")
        for a, b in gaps:
            said = " ".join(w["w"] for w in words if a <= (w["s"] + w["e"]) / 2 < b)
            said = (said[:160] + "…") if len(said) > 160 else said
            lines.append(f"- {fmt_time(a)}–{fmt_time(b)} ({b - a:.1f}s)" + (f": “{said}”" if said else ": (no speech)"))
        lines.append("")
    used = set(by_src) | {o["src"] for o in edl.get("overlays", [])}
    if inv_path.exists():
        unused = [f["file"] for f in json.loads(inv_path.read_text())["files"] if f["file"] not in used]
        if unused:
            lines += ["**Files not used at all:**", *[f"- `{u}`" for u in unused], ""]
    dst.write_text("\n".join(lines) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("edl")
    ap.add_argument("--preview", action="store_true", help="fast 540p draft")
    ap.add_argument("--no-qc", action="store_true")
    a = ap.parse_args()
    edl_path = Path(a.edl).resolve()
    edl = json.loads(edl_path.read_text())
    for p in [s["src"] for s in edl["segments"]] + [o["src"] for o in edl.get("overlays", [])] + \
             [m["src"] for m in edl.get("music", [])] + [s["src"] for s in edl.get("sfx", [])]:
        if not (ROOT / p).exists():
            sys.exit(f"Missing file referenced in the plan: {p}")
    W, H = SIZES[(edl.get("format", "16:9"), edl.get("resolution", "1080p"))]
    if a.preview:
        W, H = (W * 540 // H // 2 * 2, 540) if W >= H else (540, H * 540 // W // 2 * 2)
    fps = int(edl.get("fps", 30))
    name = edl.get("name", "final") + ("-preview" if a.preview else "")
    out_dir = ROOT / "output" / edl["project"]
    work = out_dir / ".work" / name
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)

    # A. Conform and cut every segment (same size, frame rate, sample rate; matched loudness).
    seg_files, starts, t = [], [], 0.0
    for idx, seg in enumerate(edl["segments"]):
        print(f"  segment {idx + 1}/{len(edl['segments'])}: {seg['src']} {seg['in']}–{seg['out']}", flush=True)
        seg_files.append(render_segment(seg, idx, W, H, fps, work, a.preview))
        starts.append(t)
        t += float(seg["out"]) - float(seg["in"])
    total = t
    (work / "list.txt").write_text("".join(f"file '{p.name}'\n" for p in seg_files))
    base = work / "base.mkv"
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(work / "list.txt"), "-c", "copy", str(base)])

    # B. Overlays, captions, music, sound effects.
    ov_args, ov_vf, ov_aud, last = overlay_inputs_and_filters(edl, W, H, fps, 1)
    au_args, au_af, mus, sfx = audio_inputs_and_filters(edl, 1 + len(edl.get("overlays", [])), total)
    vf = ["[0:v]null[base]"] + ov_vf
    if edl.get("captions"):
        ass = captions.build(edl, starts, W, H, work / "captions.ass")
        if ass:
            fonts = ROOT / "tools" / "fonts"
            fontsdir = f":fontsdir='{fonts}'" if fonts.is_dir() else ""
            vf.append(f"{last}subtitles='{ass}'{fontsdir}[vcap]")
            last = "[vcap]"
    vf.append(f"{last}format=yuv420p[vout]")
    af = list(au_af) + list(ov_aud)
    voice = "[0:a]"
    music_labels = []
    ducked = [k for k, (_, duck) in enumerate(mus) if duck]
    if ducked:  # the voice track drives a compressor on the music, so music dips while someone talks
        af.append(f"[0:a]asplit={1 + len(ducked)}[voice]" + "".join(f"[key{k}]" for k in ducked))
        voice = "[voice]"
    for k, (lab, duck) in enumerate(mus):
        if duck:
            af.append(f"{lab}[key{k}]sidechaincompress=threshold=0.02:ratio=4:attack=30:release=600:makeup=1[md{k}]")
            music_labels.append(f"[md{k}]")
        else:
            music_labels.append(lab)
    mix_in = [voice] + music_labels + sfx + [f"[oa{k}]" for k, ov in enumerate(edl.get("overlays", []))
                                             if ov.get("audio") and info(ov["src"]).get("has_audio")]
    af.append(f"{''.join(mix_in)}amix=inputs={len(mix_in)}:normalize=0:dropout_transition=0,"
              f"atrim=0:{total:.3f}[aout]")
    graph = ";".join(vf + af)
    (work / "graph.txt").write_text(graph)
    mixed = work / "mixed.mkv"
    enc = (["-c:v", "libx264", "-preset", "veryfast", "-crf", "26"] if a.preview
           else ["-c:v", "libx264", "-preset", "slow", "-crf", "17", "-profile:v", "high"])
    print("  compositing overlays, captions and sound…", flush=True)
    run(["ffmpeg", "-v", "error", "-y", "-i", str(base), *ov_args, *au_args, "-filter_complex_script", str(work / "graph.txt"),
         "-map", "[vout]", "-map", "[aout]", "-t", f"{total:.3f}", "-r", str(fps), *enc, "-pix_fmt", "yuv420p",
         "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-c:a", "pcm_s16le", str(mixed)])

    # C. Two-pass loudness normalisation, then the final MP4.
    target = float(edl.get("loudness", -14))
    meas = subprocess.run(["ffmpeg", "-nostats", "-i", str(mixed), "-vn", "-af",
                           f"loudnorm=I={target}:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                          capture_output=True, text=True).stderr
    j = json.loads(meas[meas.rindex("{"):meas.rindex("}") + 1])
    ln = (f"loudnorm=I={target}:TP=-1.5:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:"
          f"measured_LRA={j['input_lra']}:measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true")
    final = out_dir / f"{name}.mp4"
    run(["ffmpeg", "-v", "error", "-y", "-i", str(mixed), "-af", f"{ln},aresample={SR}", "-c:v", "copy",
         "-c:a", "aac", "-b:a", "320k", "-movflags", "+faststart", str(final)])
    write_json(out_dir / f"{name}.timeline.json", {"segments_start": starts, "total": total, "width": W, "height": H})
    cut_report(edl, starts, total, out_dir / f"{name}.report.md")
    print(f"Done: {final.relative_to(ROOT)} ({fmt_time(total)})")
    print(f"Report: {(out_dir / f'{name}.report.md').relative_to(ROOT)}")
    if not a.no_qc:
        subprocess.run([sys.executable, str(Path(__file__).with_name("qc.py")), str(final), "--edl", str(edl_path)]
                       + (["--preview"] if a.preview else []))
    if not a.preview:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
