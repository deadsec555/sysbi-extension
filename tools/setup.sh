#!/bin/bash
# Installs everything the video-edit pipeline needs. Safe to run again any time.
#   bash tools/setup.sh          install / repair
#   bash tools/setup.sh --check  only report what's missing
# Works in Claude Code cloud sessions (Linux) and on macOS/Linux computers.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOLS="$ROOT/tools"
MODELS="${VIDEO_EDIT_MODELS:-$HOME/.cache/video-edit-models}"
CHECK_ONLY=false
[ "${1:-}" = "--check" ] && CHECK_ONLY=true
problems=()

say() { echo "[video-edit setup] $*" >&2; }
have() { command -v "$1" >/dev/null 2>&1; }

# Folders (raw/ is never written to by the pipeline; projects live in subfolders).
for d in raw transcripts shotlogs animations broll audio output; do mkdir -p "$ROOT/$d"; done

# 1. FFmpeg (Finisher + Viewer)
if ! have ffmpeg || ! have ffprobe; then
  if $CHECK_ONLY; then problems+=("ffmpeg missing");
  elif have brew; then brew install ffmpeg;
  elif have apt-get; then (sudo -n true 2>/dev/null && SUDO=sudo || SUDO=""; $SUDO apt-get update -qq && $SUDO apt-get install -y -qq ffmpeg);
  else problems+=("ffmpeg missing — install it from https://ffmpeg.org/download.html"); fi
fi

# 2. Node tools: Hyperframes (Animator), GSAP, Playwright (Researcher)
if ! have node; then
  if ! $CHECK_ONLY && have brew; then brew install node; else problems+=("Node.js missing — install from https://nodejs.org"); fi
fi
if have npm && ! $CHECK_ONLY; then
  (cd "$TOOLS" && npm install --no-audit --no-fund --loglevel=error >/dev/null) || problems+=("npm install in tools/ failed")
fi
[ -x "$TOOLS/node_modules/.bin/hyperframes" ] || problems+=("Hyperframes not installed")

# Chrome for Hyperframes renders and page captures: reuse a local Chromium when there is one.
HS=$(ls -d /opt/pw-browsers/chromium_headless_shell-*/chrome-linux/headless_shell 2>/dev/null | head -1)
if [ -z "$HS" ] && ! $CHECK_ONLY; then
  (cd "$TOOLS" && npx hyperframes browser ensure >/dev/null 2>&1) || problems+=("Chrome for Hyperframes could not be downloaded")
fi

# 3. Python tools: Parakeet (Transcriber), speaker labels, face tracking
if ! have uv && ! $CHECK_ONLY; then
  if have brew; then brew install uv; else curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1; export PATH="$HOME/.local/bin:$PATH"; fi
fi
if [ ! -x "$TOOLS/.venv/bin/python" ] && ! $CHECK_ONLY; then
  uv venv -q "$TOOLS/.venv" --python 3.12 || problems+=("could not create Python environment")
fi
if [ -x "$TOOLS/.venv/bin/python" ] && ! $CHECK_ONLY; then
  uv pip install -q --python "$TOOLS/.venv/bin/python" -r "$TOOLS/requirements.txt" || problems+=("Python packages failed to install")
fi

# 4. Models (downloaded once, ~1 GB): Parakeet TDT 0.6B v3 (int8), Silero VAD, speaker diarization
if ! $CHECK_ONLY && [ -x "$TOOLS/.venv/bin/python" ]; then
  "$TOOLS/.venv/bin/python" - "$MODELS" <<'PY' || problems+=("model download failed — huggingface.co must be reachable (see the skill's setup notes)")
import sys, os, tarfile, urllib.request, shutil
from pathlib import Path
def _short(t, e, tb):
    print(f"[video-edit setup] download error: {t.__name__}: {str(e)[:200]}", file=sys.stderr); sys.exit(1)
sys.excepthook = _short
models = Path(sys.argv[1]); models.mkdir(parents=True, exist_ok=True)
from huggingface_hub import snapshot_download
p = models / "parakeet-tdt-0.6b-v3"
if not (p / "encoder-model.int8.onnx").exists():
    snapshot_download("istupakov/parakeet-tdt-0.6b-v3-onnx", local_dir=p,
                      allow_patterns=["*.int8.onnx", "config.json", "vocab.txt"])
s = models / "silero-vad"
if not any(s.glob("*.onnx")):
    snapshot_download("istupakov/silero-vad-onnx", local_dir=s)
d = models / "diarization"; d.mkdir(exist_ok=True)
from huggingface_hub import hf_hub_download
if not (d / "segmentation.onnx").exists():
    shutil.copy(hf_hub_download("csukuangfj/sherpa-onnx-pyannote-segmentation-3-0", "model.onnx"), d / "segmentation.onnx")
if not (d / "embedding.onnx").exists():
    shutil.copy(hf_hub_download("csukuangfj/speaker-embedding-models", "nemo_en_titanet_small.onnx"), d / "embedding.onnx")
PY
fi
[ -f "$MODELS/parakeet-tdt-0.6b-v3/encoder-model.int8.onnx" ] || problems+=("Parakeet model not downloaded yet")
[ -f "$MODELS/diarization/embedding.onnx" ] || problems+=("speaker-label models not downloaded yet")

if [ ${#problems[@]} -eq 0 ]; then
  say "all tools ready (ffmpeg, Hyperframes, Parakeet, speaker labels, face tracking, page capture)."
else
  say "ready with problems:"; for p in "${problems[@]}"; do say "  - $p"; done
fi
exit 0
