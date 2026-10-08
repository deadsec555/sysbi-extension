"""Find where the subject is in a stretch of footage, so vertical/square crops keep them in frame.

Used by assemble.py when a segment has "frame": "auto". Also usable directly:
  python tools/scripts/reframe.py <video> <start> <end>
prints the focus point (x, y as 0–1 of the frame) and how much the subject moves.
"""

import subprocess
import sys
from statistics import median, pstdev

import cv2
import numpy as np

_cascades = None


def _detectors():
    global _cascades
    if _cascades is None:
        _cascades = [cv2.CascadeClassifier(cv2.data.haarcascades + n)
                     for n in ("haarcascade_frontalface_default.xml", "haarcascade_profileface.xml")]
    return _cascades


def sample_frames(path: str, start: float, end: float, n: int = 12, width: int = 640):
    dur = max(end - start, 0.1)
    for k in range(n):
        t = start + dur * (k + 0.5) / n
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", path, "-frames:v", "1",
                              "-vf", f"scale={width}:-2", "-f", "image2pipe", "-vcodec", "png", "-"],
                             capture_output=True).stdout
        if raw:
            img = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
            if img is not None:
                yield t, img


def focus(path: str, start: float, end: float) -> dict:
    """Median position of the largest face; falls back to the centre of motion, then the frame centre."""
    xs, ys, prev, motion_pts = [], [], None, []
    for _, img in sample_frames(path, start, end):
        h, w = img.shape[:2]
        gray = cv2.equalizeHist(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
        faces = []
        for det in _detectors():
            found = det.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=6, minSize=(w // 20, w // 20))
            faces += list(found) if len(found) else []
            if faces:
                break
        if faces:
            x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])
            xs.append((x + fw / 2) / w)
            ys.append((y + fh * 0.6) / h)  # aim slightly below eyes so the head isn't cut off
        if prev is not None:
            diff = cv2.absdiff(gray, prev)
            m = cv2.moments(cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)[1])
            if m["m00"] > 0:
                motion_pts.append((m["m10"] / m["m00"] / w, m["m01"] / m["m00"] / h))
        prev = gray
    if xs:
        return {"x": round(median(xs), 3), "y": round(median(ys), 3), "source": "face",
                "spread": round(pstdev(xs) if len(xs) > 1 else 0.0, 3), "hits": len(xs)}
    if motion_pts:
        return {"x": round(median(p[0] for p in motion_pts), 3), "y": round(median(p[1] for p in motion_pts), 3),
                "source": "motion", "spread": 0.0, "hits": 0}
    return {"x": 0.5, "y": 0.5, "source": "centre", "spread": 0.0, "hits": 0}


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    print(focus(sys.argv[1], float(sys.argv[2]), float(sys.argv[3])))
