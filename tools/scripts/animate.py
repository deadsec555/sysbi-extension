"""Animator: render a Hyperframes HTML animation to a transparent video clip.

Usage:
  python tools/scripts/animate.py <project> <template> <name> [--vars '{"price":"$725,000"}']
                                  [--format 16:9|9:16|1:1] [--resolution 4k|1080p] [--opaque] [--snapshot]

<template> is either a library name (a folder in .claude/skills/video-edit/library/ or
templates/, e.g. "price-card") or a path to an .html file you wrote.
Output: animations/<project>/<name>.mov (ProRes 4444 with transparency) — or .mp4 with --opaque.
The working copy (editable HTML) stays in animations/<project>/<name>/ so it can be tweaked and
re-rendered, and later saved into the skill library once the user approves it.
--snapshot only writes PNG stills of key frames (fast check before a full render).

Templates may use {{W}} and {{H}} (canvas size) and read variables with
window.__hyperframes.getVariables(); fonts/ and gsap.min.js are copied next to the HTML.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from common import ROOT, TOOLS, project_dir

SKILL = ROOT / ".claude" / "skills" / "video-edit"
CANVAS = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080)}
RES = {("16:9", "4k"): "landscape-4k", ("16:9", "1080p"): "landscape", ("9:16", "4k"): "portrait-4k",
       ("9:16", "1080p"): "portrait", ("1:1", "4k"): "square-4k", ("1:1", "1080p"): "square"}


def find_template(t: str) -> Path:
    p = Path(t)
    if p.suffix == ".html" and p.exists():
        return p.resolve()
    for base in (SKILL / "library", SKILL / "templates"):
        cand = base / t / "index.html"
        if cand.exists():
            return cand
    sys.exit(f"No template '{t}'. Library: {sorted(x.name for x in (SKILL / 'library').glob('*/'))}, "
             f"starters: {sorted(x.name for x in (SKILL / 'templates').glob('*/'))}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("template")
    ap.add_argument("name")
    ap.add_argument("--vars", default="{}")
    ap.add_argument("--format", default="16:9", choices=list(CANVAS))
    ap.add_argument("--resolution", default="4k", choices=["4k", "1080p"])
    ap.add_argument("--opaque", action="store_true", help="MP4 without transparency (full-screen cards)")
    ap.add_argument("--snapshot", action="store_true", help="only save PNG stills to check the look")
    a = ap.parse_args()

    src = find_template(a.template)
    out_dir = project_dir("animations", a.project)
    work = out_dir / a.name
    if work.exists() and work.resolve() != src.parent.resolve():
        shutil.rmtree(work)
    if not work.exists():
        shutil.copytree(src.parent, work, ignore=shutil.ignore_patterns("renders", "*.mov", "*.mp4"))
    W, H = CANVAS[a.format]
    html = (work / "index.html").read_text().replace("{{W}}", str(W)).replace("{{H}}", str(H))
    (work / "index.html").write_text(html)
    shutil.copy(TOOLS / "node_modules" / "gsap" / "dist" / "gsap.min.js", work / "gsap.min.js")
    fonts = work / "fonts"
    fonts.mkdir(exist_ok=True)
    for fam in ("montserrat", "poppins"):
        for f in (TOOLS / "node_modules" / "@fontsource" / fam / "files").glob(f"{fam}-latin-*-normal.woff2"):
            shutil.copy(f, fonts / f.name)
    if not (work / "hyperframes.json").exists():
        (work / "hyperframes.json").write_text(json.dumps({"name": a.name}))

    env = dict(os.environ, HYPERFRAMES_SKIP_SKILLS="1")
    hs = sorted(Path("/opt/pw-browsers").glob("chromium_headless_shell-*/chrome-linux/headless_shell"))
    if hs and "HYPERFRAMES_BROWSER_PATH" not in env:
        env["HYPERFRAMES_BROWSER_PATH"] = str(hs[-1])
    hf = str(TOOLS / "node_modules" / ".bin" / "hyperframes")
    lint = subprocess.run([hf, "lint", str(work)], capture_output=True, text=True, env=env)
    if lint.returncode != 0:
        print(lint.stdout[-2000:] + lint.stderr[-2000:])
    if a.snapshot:
        r = subprocess.run([hf, "snapshot", str(work)], capture_output=True, text=True, env=env, cwd=work)
        print(r.stdout[-1500:] or r.stderr[-1500:])
        print(f"Stills in {work.relative_to(ROOT)}/ — look at them before rendering.")
        return
    ext = "mp4" if a.opaque else "mov"
    dst = out_dir / f"{a.name}.{ext}"
    cmd = [hf, "render", str(work), "-o", str(dst), "--format", ext, "--resolution", RES[(a.format, a.resolution)],
           "--variables", a.vars, "--quiet"]
    if a.opaque:
        cmd += ["--quality", "delivery"]
    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if r.returncode != 0 or not dst.exists():
        sys.exit(f"Render failed:\n{r.stdout[-3000:]}\n{r.stderr[-3000:]}")
    meta = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=width,height,pix_fmt:format=duration",
                           "-of", "compact", str(dst)], capture_output=True, text=True).stdout.strip()
    print(f"Rendered {dst.relative_to(ROOT)}  ({meta.replace("stream|", "").replace("format|", "").replace(chr(10), " ")})")


if __name__ == "__main__":
    main()
