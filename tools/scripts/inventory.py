"""Step 1: inventory every file in raw/<project>/.

Usage: python tools/scripts/inventory.py <project>

Writes shotlogs/<project>/inventory.json and inventory.md. "speech" here is a
first guess from audio activity; transcribe.py confirms it by counting words.
"""

import re
import sys

from common import fmt_time, media_info, project_dir, raw_files, run, write_json


def audio_activity(path, duration: float) -> float:
    """Fraction of the file where audio is above -35 dB (rough "someone/something is making sound")."""
    if duration <= 0:
        return 0.0
    out = run(["ffmpeg", "-nostats", "-i", str(path), "-vn", "-af", "silencedetect=n=-35dB:d=0.5", "-f", "null", "-"])
    silent = sum(float(x) for x in re.findall(r"silence_duration: ([\d.]+)", out))
    starts = re.findall(r"silence_start: ([\d.]+)", out)
    ends = re.findall(r"silence_end: ([\d.]+)", out)
    if len(starts) > len(ends):  # trailing silence runs to the end
        silent += duration - float(starts[-1])
    return round(max(0.0, 1 - silent / duration), 3)


def main(project: str) -> None:
    items = []
    for f in raw_files(project):
        info = media_info(f)
        if info["kind"] in {"video", "audio"} and info["has_audio"]:
            info["audio_activity"] = audio_activity(f, info["duration"])
            info["speech_guess"] = "likely" if info["audio_activity"] > 0.35 else "unlikely"
        else:
            info["audio_activity"] = 0.0
            info["speech_guess"] = "none"
        items.append(info)
        print(f"  {info['file']}: {info['kind']} {fmt_time(info['duration'])}", flush=True)

    out = project_dir("shotlogs", project)
    total = sum(i["duration"] for i in items)
    write_json(out / "inventory.json", {"project": project, "total_raw_seconds": round(total, 3), "files": items})

    lines = [f"# Inventory: {project}", "", f"{len(items)} files, {fmt_time(total)} of raw footage.", "",
             "| File | Type | Length | Resolution | FPS | Orientation | Audio active | Speech? |",
             "|---|---|---|---|---|---|---|---|"]
    for i in items:
        res = f"{i.get('width', '-')}x{i.get('height', '-')}" if "width" in i else "-"
        lines.append(f"| {i['file']} | {i['kind']} | {fmt_time(i['duration'])} | {res} | {i.get('fps', '-')} | "
                     f"{i.get('orientation', '-')} | {int(i['audio_activity'] * 100)}% | {i['speech_guess']} |")
    (out / "inventory.md").write_text("\n".join(lines) + "\n")
    print(f"Wrote {out / 'inventory.md'}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
