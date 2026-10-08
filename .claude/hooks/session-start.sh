#!/bin/bash
# Installs the video-edit tools (FFmpeg, Hyperframes, Parakeet, ...) when a cloud session starts.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

bash "$CLAUDE_PROJECT_DIR/tools/setup.sh"

# Hyperframes renders with the Chromium that cloud sessions already have.
HS=$(ls -d /opt/pw-browsers/chromium_headless_shell-*/chrome-linux/headless_shell 2>/dev/null | head -1 || true)
if [ -n "$HS" ] && [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  echo "export HYPERFRAMES_BROWSER_PATH=\"$HS\"" >> "$CLAUDE_ENV_FILE"
  echo "export HYPERFRAMES_SKIP_SKILLS=1" >> "$CLAUDE_ENV_FILE"
fi
