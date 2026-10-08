# Editing style

The user makes real estate videos of every kind. Decided in the setup interview (2026-10-08);
learned rules are added under each type by "save what you learned".

## All videos

- **Look:** dark + one bright accent. Panels near-black `#0B0B0F` at ~88% opacity, text white
  `#FFFFFF`, secondary text `#B8B8C0`, accent yellow `#FFD60A` (highlights, prices, bars, current
  caption word). One accent only — no extra colours.
- **Fonts:** Montserrat ExtraBold/Black for headlines, prices and names; Poppins Regular/SemiBold for
  body text and small labels. (Both installed; TTFs in `tools/fonts/`, woff2 copied into animations.)
- **Animations wanted:** price/spec cards, lower-thirds (agent, interviewees, room names), logo
  intro/outro + CTA end card, map/location pins, title cards. Motion is smooth and quick
  (0.3–0.5 s in, back-out or power3 easing), never bouncy-cartoonish except the map pin drop.
- **Captions:** **shorts only** (9:16). Word-by-word highlight, 2–4 words, Montserrat bold, white with
  black outline, current word in `#FFD60A`, lower-middle of the frame clear of the face. No captions
  on 16:9 long-form unless asked.
- **Sound effects:** sparing and subtle — **only** a soft pop when something appears (card, pin,
  lower-third, title) and a click when something is clicked on screen. **No whooshes, risers, swooshes,
  dings or hits.** Quiet: about −16 to −20 dB under the voice. Never two within 2 seconds; when several
  items pop in quickly (spec chips), one pop for the group.
- **Music:** suspenseful/tense under the **hook** (first 5–15 s), then low-volume upbeat **lo-fi
  hip-hop** under speech (≈ −24 to −28 dB, ducked under the voice). Music for tours/montages is chosen
  **per property** (see Tours). Fade music out under the CTA, end on a clean button.
- **Default export:** 16:9 long-form **plus** a 9:16 short from the best moment, unless the user says
  otherwise. Loudness −14 LUFS, true peak ≤ −1.5 dBFS.
- **Pacing:** tight when someone talks, calm when showing property.
- **Zooms:** on talking heads, a subtle push-in (110–120%) every 10–20 s on key points; alternate zoom
  levels to hide jump cuts. On property shots, only slow drifts (≤ 108% over the whole shot), no punch-ins.

### Learned rules — all videos
_(none yet — G1, G2, … added by "save what you learned")_

## Property / listing tours

- **Edit type:** visual-led when there's no narration; mixed when the agent narrates.
- **Story order (default):** hook (best hero shot: twilight exterior, drone reveal, or the wow room)
  → exterior/curb appeal → entry → living → kitchen → dining → primary suite → other bedrooms/baths →
  special features (office, pool, view, yard) → neighbourhood/drone → price card + CTA end card.
- **Shots breathe:** 3–5 s each, longer for sweeping gimbal moves; cut on beats/bars of the music.
- Drop shots that are shaky, soft, show the camera operator/reflections, clutter, or blown-out
  windows when a better angle exists.
- **Price/spec card** over an exterior or hero shot early (after the hook) and again at the end with
  the CTA. Room names as small lower-thirds only if the user asks.
- **Map pin** over a real map capture or drone shot for location highlights (schools, parks, transit).
- **Music per property:** luxury/high-end → warm cinematic/ambient; family/starter homes → bright,
  upbeat acoustic/pop; modern/urban condos → chill electronic/lo-fi. Music is the lead here (≈ −16 to
  −20 dB when nobody talks, ducked under any narration). Say which mood you picked and why.

### Learned rules — tours
_(none yet — T1, T2, …)_

## Agent talking head (market updates, tips, buyer/seller advice)

- **Edit type:** speech-led. Hook in the first 5–10 s (the most surprising line or the key number),
  then the points in a clear order, CTA at the end.
- **Tight cuts:** remove every pause over ~0.3 s, all restarts and stumbles; keep natural breaths.
- **Zooms** every 10–20 s on key points, subtle (110–120%), alternating to hide jump cuts.
- **B-roll** whenever a property, place, chart or claim is mentioned: user's own clips first, then
  captured real sources (rates, news, listings, government data) with highlights.
- **Lower-third** with name + brokerage once, within the first 15 s.
- **Music:** suspense under the hook, then quiet lo-fi hip-hop.

### Learned rules — agent talking head
_(none yet — A1, A2, …)_

## Client testimonials / interviews

- **Edit type:** speech-led, speakers labelled (`--speakers auto` or the number).
- Keep the client's voice and emotion; cut questions unless needed for sense. Keep genuine
  reactions (laughs, pauses before a heartfelt line) — don't over-tighten emotion.
- Lower-third for each person on first appearance (name + "Sold in Riverside" style context).
- Cover cuts with B-roll of the home, keys handover, signage, family moments.
- **Music:** soft and warm; suspense hook only if the story has a real tension moment.

### Learned rules — testimonials
_(none yet — C1, C2, …)_

## Neighbourhood guides / open houses / events

- **Edit type:** visual-led montage (or mixed with narration); story by place or by time of day.
- Best shots 1.5–3 s on the beat; map pins for locations; title card per area/section.
- Natural sound bites (crowd, laughter, a short quote) can poke through the music for 1–2 s.
- **Music:** upbeat, matches the place's vibe; louder than under speech.

### Learned rules — neighbourhood/events
_(none yet — N1, N2, …)_

## Shorts / reels (9:16)

- Best 30–60 s moment: a single idea, the hook in the first 2 s, no slow intro, no logo sting.
- Captions on (style above). Subject kept in frame (`"frame": "auto"`; check the framing).
- Faster pacing than long-form; zoom every 5–8 s is fine here.
- End with a one-line CTA card (2–3 s), not the full end card.

### Learned rules — shorts
_(none yet — S1, S2, …)_
