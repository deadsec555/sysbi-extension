"""Shared helpers for the video-edit pipeline scripts."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
FOLDERS = ["raw", "transcripts", "shotlogs", "animations", "broll", "audio", "output"]
MEDIA_EXT = {
    ".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi", ".mts", ".m2ts", ".3gp", ".hevc",
    ".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus",
    ".jpg", ".jpeg", ".png", ".heic", ".webp",
}
MODELS = Path(os.environ.get("VIDEO_EDIT_MODELS", Path.home() / ".cache" / "video-edit-models"))


def project_dir(kind: str, project: str) -> Path:
    """Return <root>/<kind>/<project>, creating it unless it is raw/ (which is read-only)."""
    d = ROOT / kind / project
    if kind != "raw":
        d.mkdir(parents=True, exist_ok=True)
    return d


def raw_files(project: str) -> list[Path]:
    d = ROOT / "raw" / project
    if not d.is_dir():
        sys.exit(f"No folder raw/{project}/ — put the footage there first.")
    return sorted(p for p in d.rglob("*") if p.is_file() and p.suffix.lower() in MEDIA_EXT)


def run(cmd: list[str], capture: bool = True) -> str:
    r = subprocess.run(cmd, capture_output=capture, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"Command failed ({r.returncode}): {' '.join(map(str, cmd))}\n{r.stderr[-3000:]}")
    return (r.stdout or "") + (r.stderr or "")


def ffprobe(path: Path) -> dict:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)],
        capture_output=True, text=True,
    )
    return json.loads(out.stdout or "{}")


def media_info(path: Path) -> dict:
    """Summarise a media file: kind, duration, resolution (display-oriented), fps, audio."""
    p = ffprobe(path)
    v = next((s for s in p.get("streams", []) if s.get("codec_type") == "video"), None)
    a = next((s for s in p.get("streams", []) if s.get("codec_type") == "audio"), None)
    dur = float(p.get("format", {}).get("duration") or 0)
    info = {"file": str(path.relative_to(ROOT)), "duration": round(dur, 3), "has_audio": a is not None}
    if v is None:
        info["kind"] = "audio"
        return info
    w, h = int(v.get("width", 0)), int(v.get("height", 0))
    rot = 0
    for sd in v.get("side_data_list", []) or []:
        if "rotation" in sd:
            rot = int(sd["rotation"])
    rot = int(v.get("tags", {}).get("rotate", rot))
    if abs(rot) % 180 == 90:
        w, h = h, w
    num, den = (v.get("avg_frame_rate") or "0/1").split("/")
    fps = float(num) / float(den) if float(den) else 0.0
    is_image = path.suffix.lower() in {".jpg", ".jpeg", ".png", ".heic", ".webp"} or dur == 0
    if is_image:
        info["duration"] = 0.0
    info.update({
        "kind": "image" if is_image else "video",
        "width": w, "height": h, "fps": round(fps, 3),
        "orientation": "portrait" if h > w else ("square" if h == w else "landscape"),
        "vcodec": v.get("codec_name"), "pix_fmt": v.get("pix_fmt"),
        "hdr": v.get("color_transfer") in {"smpte2084", "arib-std-b67"},
        "vfr": v.get("r_frame_rate") != v.get("avg_frame_rate"),
    })
    return info


def fmt_time(t: float) -> str:
    m, s = divmod(max(t, 0), 60)
    h, m = divmod(int(m), 60)
    return f"{h}:{m:02d}:{s:05.2f}" if h else f"{m}:{s:05.2f}"


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def need(tool: str) -> None:
    if not shutil.which(tool):
        sys.exit(f"{tool} is not installed. Run: bash tools/setup.sh")
