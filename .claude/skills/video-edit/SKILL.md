---
name: video-edit
description: Edit raw footage into a finished video for the user's real estate channel (listing tours, agent talking heads, client testimonials, neighbourhood/event videos, shorts). Use whenever the user gives footage, a project folder in raw/, Tella recording names, or a brief and asks for a video, cut, short, reel, edit, re-edit, or feedback changes; also when they say "save what you learned" or approve an animation. Covers transcription (Parakeet), shot logs, cutting, zooms, Hyperframes animations, source B-roll, Tella, Epidemic Sound music/SFX, FFmpeg assembly, QC and export.
---

# Video edit

You are the editor and coordinator. The user is **not technical**: talk in plain words, do every
technical step yourself, and when something needs their hands, give one step at a time and wait.

Before every edit, read **[style.md](style.md)** (their style + numbered rules learned from feedback)
and **[brand.md](brand.md)** (name, logo, contact). They override anything generic below.

## The crew (tools)

All commands run from the repo root. `PY=tools/.venv/bin/python`.

| Job | Tool | Command |
|---|---|---|
| Inventory | ffprobe | `$PY tools/scripts/inventory.py <project>` |
| Transcriber | NVIDIA Parakeet TDT 0.6B v3 (local, ONNX) | `$PY tools/scripts/transcribe.py <project> [--speakers auto\|N]` |
| Viewer | FFmpeg scene/motion/audio analysis + your eyes | `$PY tools/scripts/shotlog.py <project>` then Read the frames |
| Animator | Hyperframes (HTML → video, up to 4K, transparent) | `$PY tools/scripts/animate.py <project> <template> <name> --vars '{…}'` |
| Researcher | Chromium via Playwright (real pages only) | `node tools/scripts/capture.mjs <url> broll/<project>/<name> --highlight "exact text"` |
| Screen editor | Tella connector (`mcp__*tella*` tools) | see [connectors.md](connectors.md) |
| Sound designer | Epidemic Sound connector | see [connectors.md](connectors.md) |
| Beat finder | Hyperframes beats | `$PY tools/scripts/beats.py audio/<project>/<track>.mp3` |
| Finisher | FFmpeg | `$PY tools/scripts/assemble.py output/<project>/<name>.edl.json [--preview]` |
| QC | FFmpeg | runs automatically after assemble; or `$PY tools/scripts/qc.py <video> --edl <plan>` |

Edit-plan (EDL) format: the docstring at the top of `tools/scripts/assemble.py`. Read it once per session.

## Hard rules

1. **Never modify, move, rename or delete anything in `raw/`.** Read only. (A hook enforces this.)
   New footage may be *added* (`mkdir`, `cp -n`). Every output goes in the matching folder:
   `transcripts/ shotlogs/ animations/ broll/ audio/ output/`, always inside `<folder>/<project>/`.
2. **Only real sources as B-roll.** Never recreate, mock up or retype a post, page, listing or article.
   Capture the original. If it can't be captured (login wall, removed), tell the user and ask for a
   screenshot or a different source — don't fake it. Record every source URL in the edit report.
3. **Plan first for anything longer than 3 minutes (final length):** show the plan (edit type,
   structure, what's being cut, music, animations) and **wait for approval before rendering**.
4. **After every render**, report raw length vs final length and what was cut (from `<name>.report.md`).
5. **Nothing reaches the user before QC passes** (`Must fix` empty). Fix and re-render first.
6. Sound effects and music follow style.md exactly — sparing and subtle is the rule.

## Step 0 — Check the workshop (every session, ~10 s)

1. `bash tools/setup.sh --check`. If it lists problems, run `bash tools/setup.sh`. If models still
   can't download, the environment's network is blocking huggingface.co / github.com — tell the user
   (one step: environment settings → Network access → **Full**, then start a new session).
2. Look for connector tools with ToolSearch: `tella`, `epidemic`. Note which are available.
3. Footage: the project lives in `raw/<project>/`. If the user attached files in chat or named files
   elsewhere, copy them in with `cp -n` (never overwrite). If footage is missing, ask for it — one step.
   Cloud sessions can't see the user's computer; files must be uploaded/attached, or the user works
   locally (see connectors.md → "Working locally").

## Step 1 — Inventory

Run `inventory.py`. Tell the user in one short table: files, type, length, resolution, speech yes/no.
Flag oddities: vertical phone clips, 60 fps, HDR (iPhone), very low resolution, no audio.

## Step 2 — Understand the footage

**Speech** (speech_guess likely, or the user says someone talks): `transcribe.py`. Add `--speakers auto`
(or the number) for interviews/testimonials/podcasts. Read `transcripts/<project>/<file>.md`:
- `#N` = index of the phrase's first word in the `.json` (word-level `s`/`e` times are in seconds).
- `⟲ POSSIBLE RETAKE` = the user restarted the line; the *later* take is usually the keeper.
- `~word~` = low confidence (mumble, noise, name) — check context; spell names from the brief.
- If the file says **NO SPEECH**, treat it as visual footage.

**Visual** (no/little speech, B-roll, tours, events): `shotlog.py`, then **look**: Read
`shotlogs/<project>/frames/<file>_sheet.jpg` and the individual shot frames. For every shot fill in
`description` (what's in it: room, angle, subject, movement), `quality` (good/ok/poor + why: soft focus,
shaky, blown window, dark, people in frame, clutter) and `usable` (true/false) in the `.json`,
then `shotlog.py <project> --render-md` to refresh the table. Use `auto_flags` as hints, your eyes decide.

## Step 3 — Decide the edit type (say which, and why, in one line)

- **Speech-led** (talking head, tutorial, market update, testimonial, interview): the transcript is the
  spine. Build the story from the best takes; cover cuts and boring stretches with B-roll from the
  other clips (property shots, screen recordings, captured sources).
- **Visual-led** (listing tour without narration, neighbourhood montage, open house, event): pick the
  best usable shots from the shot logs, order them into a story (see style.md for the tour order), and
  cut to the beat of the music (`beats.py`: cut on `beats`, change scene on `bars`).
- **Mixed** (agent narrates a tour, voice-over plus footage): speech sets the structure and timing;
  visual clips illustrate what is being said at that moment.

## Step 4 — Cut (write the EDL)

Write `output/<project>/<name>.edl.json`. Every segment and overlay gets a short `note` (why it's there).

Speech cutting method:
- Use word timestamps. Cut **between** words, never inside one: start a segment ~0.08 s before the
  first kept word's `s`, end it ~0.12 s after the last kept word's `e` (less if the next word follows
  immediately). Keep a natural breath (0.15–0.3 s) between sentences, no dead air beyond that.
- Remove: false starts and restarts (keep the last clean take), stumbles, "um/uh/you know" when they
  stand alone, repeated sentences, off-topic asides, "is it recording?", pre-roll and post-roll.
- Keep meaning intact. Never splice words from different sentences to make the person say
  something they didn't say.
- A jump cut on a talking head should be hidden: alternate subtle zoom levels across consecutive
  segments (1.0 → 1.12 → 1.0) or cover with B-roll.
- Interviews: keep the question only when the answer doesn't make sense without it; lower-third each
  speaker on first appearance.

Zooms, captions, B-roll and graphics follow style.md for the video type.

## Step 5 — Animations, B-roll, sources

- **Animations**: reuse the approved **library** first (`library/README.md`). Else start from a starter in
  `templates/` (title-card, lower-third, price-card, logo-sting, cta-endcard, map-pin) or write new HTML.
  Render: `animate.py <project> <template> <name> --vars '{…}' --format <16:9|9:16|1:1>` (4K transparent
  `.mov` by default). Check a frame (composite over the actual footage frame and Read it) before using.
  Authoring rules for new HTML: Hyperframes docs (`npx hyperframes docs gsap|compositions|data-attributes`,
  run inside `tools/`); register `window.__timelines["main"]`, deterministic GSAP only, transparent
  background, use `vmin` sizes and `{{W}}`/`{{H}}` so the same file works for 16:9 and 9:16.
- **Source B-roll** (user mentions a claim, announcement, rate change, listing, product, article):
  find the original (official post, press release, MLS/listing page, government data, paper),
  `capture.mjs` it with `--highlight` on the exact relevant line, use the `.mp4` (scroll) or `.png` with a
  slow zoom into the highlight box from `<name>.json` `boxes`. Cite the URL in the report.
- **Tella** recordings: see connectors.md.

## Step 6 — Sound

Follow style.md. Get music and SFX from Epidemic Sound (connectors.md) into `audio/<project>/`.
Music under speech is ducked automatically (`"duck": true`). Put a soft pop on each animation's
`sfx_cues_pop` times (in its `meta.json`, offset by the overlay's `at`), and a click only where something
is actually clicked on screen. Never more than one SFX in any 2-second window.

## Step 7 — Assemble, QC, export

1. Over 3 minutes: show the plan, wait for approval. Otherwise go straight on.
2. `assemble.py … --preview` (fast 540p). Read `<name>-preview.qc.md` and the `.qc.jpg` contact sheet.
   Fix anything under **Must fix**; judge each **Check** item.
3. Full render: `assemble.py …` (default 1080p; `"resolution": "4k"` when the footage is 4K and the user
   wants 4K). It QCs again. Rendering is slow on this machine (roughly real-time ×2–5 at 1080p) —
   tell the user roughly how long and run it in the background.
4. Formats: if the user doesn't say, deliver **16:9 long-form + one 9:16 short** (the best 30–60 s moment,
   `"format": "9:16"`, `"frame": "auto"` keeps the face/subject in frame; check the framing with frames).
   1:1 only when asked.
5. Report to the user (from `report.md`):
   - **Raw: X:XX → Final: X:XX** (percent kept) for each output,
   - edit type chosen and the structure in 3–6 bullets,
   - what was cut (grouped: retakes, stumbles, dead air, off-topic, weak shots) with a few examples,
   - sources used (URLs), music tracks, anything you need from them (logo, contact details, a missing shot).
   Send the video file(s) and the report.

## Feedback loop

The user gives **timestamped notes on the final video** (e.g. "0:42 cut is too abrupt").
1. Map each timestamp to the segment/overlay with `<name>.report.md` → "Timeline".
2. Apply every note, re-render, QC, and report what changed per note + new raw-vs-final lengths.
3. Keep a running list of the notes and what you did in `output/<project>/feedback.md`.

**"save what you learned"** → for each lesson from the feedback in this conversation, write a general,
reusable rule (not "0:42 in the Maple Ave video" but "never cut within 0.2 s after a sentence ends
on a talking head") and append it to style.md under the matching video type's
**Learned rules**, continuing the numbering (`T1, T2…` tours, `A1…` agent talking head, `C1…`
testimonials, `N1…` neighbourhood/event, `S1…` shorts, `G1…` all videos). Skip duplicates; if a new
rule contradicts an old one, replace the old one and say so. Then show the user the new rules.

**Animation approved** ("love that price card", "keep this one") → copy its working folder
`animations/<project>/<name>/` to `.claude/skills/video-edit/library/<descriptive-name>/` (drop renders),
update its `meta.json` (`status: approved`, date, video it was used in, variables, sfx cues) and add a
line to `library/README.md`. Prefer library items over starters from then on.

Rules, library and brand changes are only kept for future sessions if committed and pushed:
after saving, commit (`git add .claude/skills/video-edit && git commit`) and push the branch.
