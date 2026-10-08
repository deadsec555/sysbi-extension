"""Find the beats in a music track so visual-led edits can cut on the beat.

Usage: python tools/scripts/beats.py audio/<project>/<track>.mp3
Writes audio/<project>/<track>.beats.json: {"bpm": 120.2, "beats": [0.499, 0.998, ...],
"strong": [...beats with strength >= 0.8...], "bars": [...every 4th beat...]}
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from common import TOOLS, media_info


def main(track: str) -> None:
    src = Path(track).resolve()
    dur = media_info(src)["duration"]
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        shutil.copy(src, d / src.name)
        (d / "hyperframes.json").write_text('{"name":"beats"}')
        (d / "index.html").write_text(
            f'<!doctype html><html><body><audio id="music" data-timeline-role="music" src="{src.name}" data-start="0" data-duration="{dur}" '
            f'data-track-index="0"></audio><div id="root" data-composition-id="main" data-start="0" '
            f'data-duration="{dur}" data-width="1920" data-height="1080"></div>'
            '<script>window.__timelines={main:{seek(){},duration(){return 0}}};</script></body></html>')
        r = subprocess.run([str(TOOLS / "node_modules" / ".bin" / "hyperframes"), "beats", str(d), "--json"],
                           capture_output=True, text=True, env=dict(os.environ, HYPERFRAMES_SKIP_SKILLS="1"))
        res = json.loads(r.stdout[r.stdout.index("{"):]) if "{" in r.stdout else {}
        if not res.get("ok"):
            sys.exit(f"Beat detection failed: {r.stdout[-1000:]} {r.stderr[-1000:]}")
        beats = json.loads((d / res["file"]).read_text())["beats"]
    times = [b["time"] for b in beats]
    out = {"track": str(src.name), "bpm": res.get("bpm"), "beats": times,
           "strong": [b["time"] for b in beats if b.get("strength", 0) >= 0.8], "bars": times[::4]}
    dst = src.with_suffix(".beats.json")
    dst.write_text(json.dumps(out, indent=1))
    print(f"{len(times)} beats, ~{res.get('bpm')} BPM → {dst}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
