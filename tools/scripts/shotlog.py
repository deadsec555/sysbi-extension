"""Step 2b: build a draft shot log for visual footage (the "Viewer").

Usage: python tools/scripts/shotlog.py <project> [--file NAME] [--threshold 0.3]

For each video in raw/<project>/:
  - detects scene changes (long shots are split into ~5 s pieces),
  - measures brightness, motion, blur and audio level per shot,
  - saves a frame from each shot plus a contact sheet per file,
  - writes shotlogs/<project>/<stem>.json and <stem>.md.
The "what's in the shot" and "usable" columns are left for Claude to fill in after
looking at the frames (Read the .jpg files), then saved back into the same files.
"""

import argparse
import re
import subprocess
from statistics import mean, pstdev

from common import ROOT, fmt_time, media_info, project_dir, raw_files, write_json

MAX_SHOT = 5.0


def scene_cuts(path, threshold: float) -> list[float]:
    r = subprocess.run(["ffmpeg", "-nostats", "-i", str(path), "-an", "-vf",
                        f"scale=320:-2,select='gt(scene,{threshold})',showinfo", "-f", "null", "-"],
                       capture_output=True, text=True)
    return [float(t) for t in re.findall(r"pts_time:([\d.]+)", r.stderr)]


def frame_stats(path) -> list[dict]:
    """5 samples/second: brightness (YAVG), frame difference (YDIF, ~motion) and blur."""
    r = subprocess.run(["ffmpeg", "-nostats", "-i", str(path), "-an", "-vf",
                        "fps=5,scale=480:-2,signalstats,blurdetect,metadata=print:file=-", "-f", "null", "-"],
                       capture_output=True, text=True)
    rows, cur = [], None
    for line in r.stdout.splitlines():
        if m := re.search(r"pts_time:([\d.]+)", line):
            cur = {"t": float(m.group(1))}
            rows.append(cur)
        elif cur is not None and "=" in line:
            k, v = line.split("=", 1)
            key = k.rsplit(".", 1)[-1]
            if key in {"YAVG", "YDIF", "blur"}:
                try:
                    cur[key] = float(v)
                except ValueError:
                    pass
    return rows


def audio_levels(path) -> list[tuple[float, float]]:
    """RMS level in dB for each 0.5 s window."""
    r = subprocess.run(["ffmpeg", "-nostats", "-i", str(path), "-vn", "-af",
                        "aresample=16000,asetnsamples=n=8000:p=0,astats=metadata=1:reset=1,"
                        "ametadata=print:key=lavfi.astats.Overall.RMS_level:file=-", "-f", "null", "-"],
                       capture_output=True, text=True)
    out, t = [], None
    for line in r.stdout.splitlines():
        if m := re.search(r"pts_time:([\d.]+)", line):
            t = float(m.group(1))
        elif "RMS_level=" in line and t is not None:
            v = line.split("=", 1)[1]
            out.append((t, -90.0 if v in {"-inf", "inf"} else float(v)))
    return out


def save_frame(path, t: float, dst) -> None:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(path), "-frames:v", "1",
                    "-vf", "scale=640:-2", "-q:v", "4", str(dst)], check=False)


def contact_sheet(path, shots, dst) -> None:
    n = len(shots)
    cols = 4
    rows = max(1, -(-n // cols))
    # Pick the middle frame of each shot via select on timestamps.
    sel = "+".join(f"between(t,{(s['s'] + s['e']) / 2:.3f},{(s['s'] + s['e']) / 2 + 0.25:.3f})" for s in shots)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(path), "-an", "-vf",
                    f"select='{sel}',scale=360:-2,drawtext=text='%{{pts\\:hms}}':x=6:y=6:fontsize=20:"
                    f"fontcolor=white:box=1:boxcolor=black@0.6,tile={cols}x{rows}:padding=4",
                    "-frames:v", "1", "-fps_mode", "vfr", "-q:v", "4", str(dst)], check=False)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--file")
    ap.add_argument("--render-md", action="store_true", help="only rebuild the .md files from the .json files")
    ap.add_argument("--threshold", type=float, default=0.3, help="scene-change sensitivity (lower = more cuts)")
    a = ap.parse_args()
    out = project_dir("shotlogs", a.project)
    frames_dir = out / "frames"
    frames_dir.mkdir(exist_ok=True)
    if a.render_md:
        for j in sorted(out.glob("*.json")):
            if j.stem != "inventory" and (not a.file or j.stem == a.file.rsplit(".", 1)[0]):
                render_md(out, j.stem)
        return

    for f in raw_files(a.project):
        if a.file and f.name != a.file:
            continue
        info = media_info(f)
        if info["kind"] != "video":
            continue
        print(f"  {f.name}: analysing {fmt_time(info['duration'])}…", flush=True)
        dur = info["duration"]
        bounds = [0.0] + [t for t in scene_cuts(f, a.threshold) if 0.3 < t < dur - 0.3] + [dur]
        shots = []
        for s, e in zip(bounds, bounds[1:]):
            n = max(1, round((e - s) / MAX_SHOT))
            step = (e - s) / n
            shots += [{"s": round(s + k * step, 3), "e": round(s + (k + 1) * step, 3),
                       "new_scene": k == 0} for k in range(n)]
        stats = frame_stats(f)
        audio = audio_levels(f) if info["has_audio"] else []
        blur_all = sorted(x["blur"] for x in stats if "blur" in x) or [0]
        for i, sh in enumerate(shots):
            fs = [x for x in stats if sh["s"] <= x["t"] < sh["e"]] or stats[:1]
            au = [db for t, db in audio if sh["s"] <= t < sh["e"]]
            y = mean(x.get("YAVG", 0) for x in fs) if fs else 0
            motion = [x.get("YDIF", 0) for x in fs]
            blur = mean(x.get("blur", 0) for x in fs) if fs else 0
            sh.update({
                "n": i, "brightness": round(y, 1), "motion": round(mean(motion), 2) if motion else 0,
                "shake": round(pstdev(motion), 2) if len(motion) > 1 else 0, "blur": round(blur, 2),
                "audio_db": round(mean(au), 1) if au else None,
            })
            flags = []
            if y < 35:
                flags.append("dark")
            if y > 225:
                flags.append("overexposed")
            if blur_all[-1] and blur >= blur_all[int(len(blur_all) * 0.85)] and blur > blur_all[len(blur_all) // 2] * 1.3:
                flags.append("soft/blurry")
            if sh["motion"] > 25 or sh["shake"] > 12:
                flags.append("fast motion/shaky")
            if sh["motion"] < 0.3:
                flags.append("static")
            if sh["e"] - sh["s"] < 1.0:
                flags.append("very short")
            sh["auto_flags"] = flags
            sh["frame"] = f"frames/{f.stem}_{i:03d}.jpg"
            save_frame(f, (sh["s"] + sh["e"]) / 2, out / sh["frame"])
            sh["description"] = ""   # filled in by Claude after viewing the frame
            sh["quality"] = ""       # filled in by Claude: good / ok / poor + why
            sh["usable"] = None      # filled in by Claude: true / false
        sheet = f"frames/{f.stem}_sheet.jpg"
        contact_sheet(f, shots[:48], out / sheet)
        write_json(out / f"{f.stem}.json", {"file": str(f.relative_to(ROOT)), "info": info,
                                            "contact_sheet": sheet, "shots": shots})
        render_md(out, f.stem)
        print(f"    → shotlogs/{a.project}/{f.stem}.md ({len(shots)} shots)")


def render_md(out, stem: str) -> None:
    """(Re)write <stem>.md from <stem>.json — run again after filling in descriptions."""
    import json
    log = json.loads((out / f"{stem}.json").read_text())
    info, shots, sheet, dur = log["info"], log["shots"], log["contact_sheet"], log["info"]["duration"]
    lines = [f"# Shot log: {stem}", "",
             f"{info['width']}x{info['height']} @ {info['fps']} fps · {fmt_time(dur)} · {len(shots)} shots · "
             f"contact sheet: {sheet}", "",
             "| # | Time | What's in the shot | Quality | Usable | Auto flags | Motion | Audio dB |",
             "|---|---|---|---|---|---|---|---|"]
    for sh in shots:
        lines.append(f"| {sh['n']} | {fmt_time(sh['s'])}–{fmt_time(sh['e'])} | {sh['description'] or '_(to fill)_'} | "
                     f"{sh['quality']} | {'' if sh['usable'] is None else ('yes' if sh['usable'] else 'no')} | "
                     f"{', '.join(sh['auto_flags'])} | {sh['motion']} | {sh['audio_db']} |")
    (out / f"{stem}.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
