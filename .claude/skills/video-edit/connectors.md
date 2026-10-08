# Connectors and environment

Find connector tools with ToolSearch (`tella`, `epidemic`, `hyperframes`). Connector tools are named
`mcp__<connector>__<tool>`; read each tool's description before first use.

## Tella (screen recordings)

When the user gives Tella recording names:
1. Search/list their videos with the Tella tools and open the named recordings.
2. Do the screen-recording edit **in Tella**: trim mistakes and dead air (use Tella's transcript), add
   zooms on the clicks/areas being discussed, set the layout (screen + camera bubble / side-by-side /
   screen only) per section, follow style.md (accent colour, sparing SFX).
3. Export/download the finished Tella video into `broll/<project>/` (or `raw/<project>/` with `cp -n` if it
   is the main footage — never overwrite) and include it in the edit like any clip.
4. Report what you changed in Tella.
If the Tella tools are not available: tell the user to turn the connector on (claude.ai →
Settings → Connectors → Tella → Connect) or to export the recording from Tella and attach it.

## Epidemic Sound (music + SFX)

Not in the connector directory as of setup (2026-10-08). If tools matching `epidemic` exist, use them to
search by mood/genre/BPM/length (style.md), download into `audio/<project>/`, and note track title +
artist in the report. If they don't exist:
- ask the user (one step at a time) to download from epidemicsound.com the tracks you specify
  (give exact search terms: e.g. "suspense, tension, cinematic, 90 BPM, 15 s" for a hook and
  "lo-fi hip hop, chill, upbeat, 85–95 BPM" for under speech; "pop", "click" in Sound Effects), then
  attach them; save them into `audio/<project>/` (music) and `audio/_sfx/` (reusable SFX).
- keep a reusable SFX kit in `audio/_sfx/` (soft pop, mouse click) once the user provides it.
Never use music the user hasn't licensed.

## Hyperframes connector (optional)

The local Hyperframes CLI is the main animator (renders 4K transparent clips on this machine). If the
"HyperFrames by HeyGen" connector is on, it may be used for quick previews; final renders stay local
so they match the edit exactly.

## Network / models

Parakeet and speaker-label models download from huggingface.co and github.com on first setup
(~1 GB). Captures need the open web. If either is blocked: the environment's Network access must be
**Full** (cloud environment settings → Edit → Network access), then start a new session.

## Working locally (optional)

Cloud sessions can only edit footage that's uploaded to the session, and the files vanish when the
session ends. For big shoots the user can run this same folder on their own computer with the Claude
desktop app (Code tab, local folder): clone the repo, run `bash tools/setup.sh` once (needs Homebrew on
a Mac), then use the same skill. Rendering is much faster on a recent Mac.
