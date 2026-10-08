"""Quality check a rendered video before the user sees it.

Usage: python tools/scripts/qc.py output/<project>/<name>.mp4 [--edl <plan.edl.json>] [--preview]

Checks: decode errors, black frames, frozen video, audio dropouts, audio/video length
mismatch (sync drift), unexpected single-frame flashes or jumps (glitches), loudness and
true peak. Also writes a contact sheet (one frame every few seconds) to look at.
Writes <name>.qc.md next to the video and exits non-zero if anything must be fixed.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from common import ffprobe, fmt_time


def ff(args: list[str]) -> str:
    return subprocess.run(["ffmpeg", "-nostats", "-hide_banner", *args], capture_output=True, text=True).stderr


def expected_cuts(edl_path: Path | None, video: Path) -> list[float]:
    """Times where the plan intentionally changes picture (segment joins, overlays in/out)."""
    if not edl_path:
        return []
    edl = json.loads(edl_path.read_text())
    tl = video.with_name(video.stem + ".timeline.json")
    starts = json.loads(tl.read_text())["segments_start"] if tl.exists() else []
    cuts = list(starts)
    for ov in edl.get("overlays", []):
        at = float(ov["at"])
        cuts += [at, at + float(ov.get("dur") or 0)]
    for seg, s in zip(edl.get("segments", []), starts):
        for z in seg.get("zooms", []):
            if float(z.get("ease", 0.3)) < 0.05:  # punch-in zooms are intentional jumps
                cuts += [s + float(z["at"]), s + float(z["at"]) + float(z["dur"])]
    return sorted(cuts)


def cut_points_check(edl_path: Path, video: Path, must_fix: list, warn: list, ok: list) -> None:
    """Every segment start/end must fall between words, not inside one (uses the word timestamps)."""
    from common import ROOT
    edl = json.loads(edl_path.read_text())
    tl = video.with_name(video.stem + ".timeline.json")
    starts = json.loads(tl.read_text())["segments_start"] if tl.exists() else [0] * len(edl["segments"])
    bad, tight, checked = [], [], 0
    for seg, o in zip(edl["segments"], starts):
        tpath = ROOT / "transcripts" / edl["project"] / f"{Path(seg['src']).stem}.json"
        if not tpath.exists():
            continue
        words = json.loads(tpath.read_text())["words"]
        for edge, t_src, t_out in (("starts", float(seg["in"]), o),
                                   ("ends", float(seg["out"]), o + float(seg["out"]) - float(seg["in"]))):
            checked += 1
            for w in words:
                if w["s"] + 0.03 < t_src < w["e"] - 0.03:
                    bad.append(f"{fmt_time(t_out)}: segment {edge} inside the word “{w['w']}” ({seg['src']} @ {t_src:.2f}s)")
                    break
                gap = (w["s"] - t_src) if edge == "starts" else (t_src - w["e"])
                if 0 <= gap < 0.03 and ((edge == "starts" and w["s"] >= t_src) or (edge == "ends" and w["e"] <= t_src)):
                    tight.append(f"{fmt_time(t_out)} ({w['w']})")
                    break
    if bad:
        must_fix.append("Cuts that chop a word: " + "; ".join(bad[:10]))
    if tight:
        warn.append("Cuts very tight to a word (<30 ms, may sound clipped): " + ", ".join(tight[:10]))
    if checked and not bad:
        ok.append(f"All {checked} cut points fall between words.")


def speech_check(v: Path, edl_path: Path, must_fix: list, warn: list, ok: list) -> None:
    import difflib
    import tempfile

    import captions
    import transcribe

    edl = json.loads(edl_path.read_text())
    tl = v.with_name(v.stem + ".timeline.json")
    if not tl.exists():
        return
    expected = captions.timeline_words(edl, json.loads(tl.read_text())["segments_start"])
    if not expected:
        return
    norm = lambda t: re.sub(r"[^\w']", "", t.lower())
    d = tempfile.TemporaryDirectory()
    wav = Path(d.name) / "out.wav"
    transcribe.extract_wav(v, wav)
    asr = transcribe.load_asr()
    heard = [w for seg in asr.recognize(str(wav)) for w in transcribe.words_from_segment(seg)]

    def heard_alone(s: float, e: float, words: list[str]) -> bool:
        """Listen again to just this moment: long chunks can make the model skip a phrase that is there."""
        import soundfile as sf
        audio, sr = sf.read(str(wav), dtype="float32")
        clip = audio[max(int((s - 0.4) * sr), 0):int((e + 0.4) * sr)]
        text = " ".join(r.text for r in asr.recognize(clip))
        got = {norm(x) for x in text.split()}
        return sum(norm(w) in got for w in words) >= 0.7 * len(words)

    a_, b_ = [norm(w["w"]) for w in expected], [norm(w["w"]) for w in heard]
    sm = difflib.SequenceMatcher(None, a_, b_, autojunk=False)
    missing, offsets = [], []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            offsets += [heard[j]["s"] - expected[i]["s"] for i, j in zip(range(i1, i2), range(j1, j2))]
        elif tag in ("delete", "replace") and i2 - i1 >= 1:
            gone = " ".join(w["w"] for w in expected[i1:i2])
            if (tag == "delete" or (i2 - i1) > 2 * max(j2 - j1, 1)) and not heard_alone(
                    expected[i1]["s"], expected[i2 - 1]["e"], [w["w"] for w in expected[i1:i2]]):
                missing.append(f"{fmt_time(expected[i1]['s'])} “{gone[:80]}”")
    d.cleanup()
    match = sum(n for *_, n in sm.get_matching_blocks()) / max(len(a_), 1)
    if missing:
        (must_fix if len(missing) > 2 or match < 0.85 else warn).append(
            "Words in the plan not heard in the output (clipped cut?): " + "; ".join(missing[:8]))
    if offsets:
        offsets.sort()
        med = offsets[len(offsets) // 2]
        spread = offsets[int(len(offsets) * 0.9)] - offsets[int(len(offsets) * 0.1)]
        if abs(med) > 0.15 or spread > 0.4:
            must_fix.append(f"Speech is out of place: words land {med * 1000:+.0f} ms from where the plan puts them "
                            f"(spread {spread * 1000:.0f} ms) — audio sync problem.")
        else:
            ok.append(f"Speech re-checked: {match * 100:.0f}% of planned words heard, in place (offset {med * 1000:+.0f} ms).")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--edl")
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--no-speech-check", action="store_true")
    a = ap.parse_args()
    v = Path(a.video).resolve()
    must_fix, warn, ok = [], [], []

    p = ffprobe(v)
    vs = next((s for s in p["streams"] if s["codec_type"] == "video"), None)
    as_ = next((s for s in p["streams"] if s["codec_type"] == "audio"), None)
    if not vs or not as_:
        must_fix.append("Missing video or audio stream.")
    dur = float(p["format"]["duration"])
    num, den = vs["avg_frame_rate"].split("/")
    fps = float(num) / float(den)
    frame = 1 / fps

    # Sync: stream lengths and start times must match within a frame.
    vd, ad = float(vs.get("duration", dur)), float(as_.get("duration", dur)) if as_ else 0
    vst, ast = float(vs.get("start_time", 0)), float(as_.get("start_time", 0)) if as_ else 0
    if abs(vd - ad) > 2 * frame or abs(vst - ast) > frame:
        must_fix.append(f"Audio/video length mismatch: video {vd:.3f}s from {vst:.3f}, audio {ad:.3f}s from {ast:.3f} "
                        f"(drift {abs(vd - ad) * 1000:.0f} ms).")
    else:
        ok.append(f"Audio and video line up (difference {abs(vd - ad) * 1000:.0f} ms).")
    if a.edl:
        tl = v.with_name(v.stem + ".timeline.json")
        if tl.exists():
            planned = json.loads(tl.read_text())["total"]
            if abs(planned - dur) > 0.1:
                must_fix.append(f"Length {dur:.2f}s differs from the plan ({planned:.2f}s).")

    # Decode errors.
    errs = subprocess.run(["ffmpeg", "-v", "error", "-i", str(v), "-f", "null", "-"], capture_output=True, text=True).stderr
    if errs.strip():
        must_fix.append("Decode errors: " + errs.strip().splitlines()[0][:200])
    else:
        ok.append("Decodes cleanly, no corrupt frames.")

    # One pass for picture checks + one for audio checks.
    vout = ff(["-i", str(v), "-an", "-vf", "blackdetect=d=0.1:pic_th=0.97,freezedetect=n=0.002:d=1.5", "-f", "null", "-"])
    blacks = [(float(s), float(e)) for s, e in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", vout)]
    for s, e in blacks:
        if s < 0.05 and e < 0.6 or e > dur - 0.6:
            continue  # short fade at the very start/end is fine
        must_fix.append(f"Black frames {fmt_time(s)}–{fmt_time(e)} ({(e - s) * 1000:.0f} ms).")
    fs = [float(x) for x in re.findall(r"freeze_start: ([\d.]+)", vout)]
    fe = [float(x) for x in re.findall(r"freeze_end: ([\d.]+)", vout)] + [dur]
    for s, e in zip(fs, fe):
        warn.append(f"Picture frozen {fmt_time(s)}–{fmt_time(e)} ({e - s:.1f}s) — fine if it's a still/title, "
                    "otherwise a stalled clip.")

    # Glitches: picture jumps where the plan has no cut, especially a jump that jumps back 1–3 frames later.
    scd = subprocess.run(["ffmpeg", "-nostats", "-i", str(v), "-an", "-vf",
                          "scale=320:-2,scdet=threshold=100,metadata=print:file=-", "-f", "null", "-"],
                         capture_output=True, text=True).stdout
    diffs = [(float(t), float(m)) for t, m in re.findall(r"pts_time:([\d.]+)\s+lavfi\.scd\.mafd=([\d.]+)", scd)]
    jumps = [t for t, m in diffs if m > 20]  # big frame-to-frame change
    planned = expected_cuts(Path(a.edl) if a.edl else None, v)
    unexpected = [t for t in jumps if not any(abs(t - c) <= 3 * frame for c in planned)]
    flashes = []
    for t1, t2 in zip(unexpected, unexpected[1:]):
        if t2 - t1 <= 3.5 * frame and not any(f[0] <= t1 <= f[1] for f in blacks):
            flashes.append(t1)
            must_fix.append(f"Flash/glitch at {fmt_time(t1)} (picture jumps and jumps back within {round((t2 - t1) * fps)} frames).")
    singles = [t for t in unexpected if not any(0 < abs(t - u) <= 3.5 * frame for u in unexpected)]
    if planned and singles:
        warn.append("Picture jumps not in the plan (could be a cut inside the source clip — check these): "
                    + ", ".join(fmt_time(t) for t in singles[:15]) + (" …" if len(singles) > 15 else ""))
    if not blacks and not flashes:
        ok.append("No black frames or flashes.")

    # Audio: dropouts, loudness, peak.
    aout = ff(["-i", str(v), "-vn", "-af", "silencedetect=n=-55dB:d=1.2,ebur128=peak=true", "-f", "null", "-"])
    ss = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", aout)]
    se = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", aout)] + [dur]
    for s, e in zip(ss, se):
        warn.append(f"Dead silence {fmt_time(s)}–{fmt_time(e)} ({e - s:.1f}s) — intended?")
    lufs = re.findall(r"I:\s+(-?[\d.]+) LUFS", aout)
    peak = re.findall(r"Peak:\s+(-?[\d.]+|-inf) dBFS", aout)
    if lufs:
        i = float(lufs[-1])
        (ok if abs(i + 14) <= 1.5 else warn).append(f"Loudness {i:.1f} LUFS (YouTube target −14).")
    if peak and peak[-1] != "-inf":
        tp = float(peak[-1])
        (ok if tp <= -1.0 else must_fix).append(f"True peak {tp:.1f} dBFS (must be ≤ −1).")

    # Speech check: re-transcribe the output and compare with the words the plan keeps
    # (catches clipped/missing words and audio drifting out of place).
    if a.edl:
        cut_points_check(Path(a.edl), v, must_fix, warn, ok)
    if a.edl and not a.no_speech_check:
        try:
            speech_check(v, Path(a.edl), must_fix, warn, ok)
        except Exception as e:  # model missing etc. — never block QC on the checker itself
            warn.append(f"Speech check skipped ({type(e).__name__}: {str(e)[:120]}).")

    # Contact sheet for a visual once-over.
    step = max(dur / 24, 1)
    sheet = v.with_name(v.stem + ".qc.jpg")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(v), "-vf",
                    f"fps=1/{step:.3f},scale=320:-2,drawtext=text='%{{pts\\:hms}}':x=4:y=4:fontsize=18:fontcolor=white:"
                    "box=1:boxcolor=black@0.6,tile=6x4:padding=3", "-frames:v", "1", "-q:v", "4", str(sheet)])

    lines = [f"# QC: {v.name}", "", f"{vs['width']}x{vs['height']} @ {fps:g} fps · {fmt_time(dur)}"
             + (" · PREVIEW" if a.preview else ""), "", f"Contact sheet: {sheet.name}", ""]
    lines += ["## Must fix", *([f"- ❌ {m}" for m in must_fix] or ["- none"]), "",
              "## Check", *([f"- ⚠️ {m}" for m in warn] or ["- none"]), "",
              "## Passed", *[f"- ✅ {m}" for m in ok]]
    out = v.with_name(v.stem + ".qc.md")
    out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    sys.exit(1 if must_fix else 0)


if __name__ == "__main__":
    main()
