---
name: ave-style-lab
description: Designs a new, unique editing style for one prospect (comedian, podcaster or creator) before making their free sample, built from their own persona and material, and checked so it never copies a paying client's style (Jackie, Brenda) or AVE's portfolio. Use when the user says "style lab", "make a unique style for <name>", "new style for this prospect", "sample for <name>", or asks for a sample edit that shouldn't look like Jackie's or another client's.
---

# AVE Style Lab

Every free sample should look like it was designed for that one person. Paying clients' styles
are theirs: Jackie's and Brenda's are never reused for a prospect. This skill produces a one-page
**style guide** for a prospect, checks it against `reserved-styles.json`, saves it, and hands it
to the edit.

The AVE fundamentals never change, whatever the style: hook in the first 2 s, captions on the
beat, the punchline never spoiled by the caption, the comedian's timing and laughs kept, 9:16,
-14 LUFS, small "AVE Studio" watermark.

## 1. Gather (ask the user only for what's missing)

- Name, handle, and the source: special, episode or set (link, Drive file or local file).
- Their socials: do they already post clips? Note the look so the sample stands out from it.
- Optional: one creator or clip they like.

## 2. Study the person

Watch or transcribe the source and write down, in a few words each:

- **Persona**: how they come across (deadpan, chaotic, warm storyteller, angry, nerdy, glam...).
- **Delivery**: pace (fast / slow), energy, how long the pauses before punchlines are.
- **Subjects**: what the bits are about (family, dating, work, crime, tech, religion...).
- **Their visual world**: stage or set colours, wardrobe, poster or special artwork, logo, fonts
  on their own posters. Pull 2–3 colours from it (eyedropper on a frame or the poster).
- **Audience**: who they're talking to.
- **Strongest 30–60 s bit** for the sample: one complete story, clear hook, clear payoff.

## 3. Find the concept

Write three candidate concepts, each one sentence that ties the look to the person's world, e.g.:

- true-crime comic → "case file": typewriter captions, evidence-tag graphics, red string lines
- tech-worker comic → "terminal": monospace captions that type on, cursor, error-dialog punchlines
- church-kid comic → "hymnal": serif captions, gold rules, verse numbers as counters
- loud podcast → "boxing poster": stacked heavy type, round-card graphics, bell hits

Pick the one that fits the persona best **and** is furthest from the reserved styles.

## 4. Write the style guide

Copy `styles/_template.md` to `styles/<prospect-slug>.md` and fill every field: concept, captions
(font, case, size, position, colour, emphasis rule, animation), hook, graphics vocabulary (3–5
motifs), framing and pacing, transitions, sound palette (from `video/public/sfx/sfx-index.json`),
end card, the one **signature move**, and a don't-list.

Pick the caption font from the pool below (free Google Fonts) unless the person's own posters
suggest a better match. Use the person's colours for the accent; AVE lime `#C8FF2E` is for the
AVE watermark only in prospect samples, because lime word accents are Jackie's look.

| Feel | Fonts |
|---|---|
| Heavy and loud | Archivo Black, Bowlby One, Anton* , Rubik Mono One |
| Editorial / dry | DM Serif Display, Instrument Serif, Fraunces |
| Techy / deadpan | JetBrains Mono, IBM Plex Mono, Space Mono |
| Playful | Lilita One, Bungee, Unbounded |
| Handmade | Permanent Marker, Caveat Brush |
| Clean modern | Bricolage Grotesque, Syne, Manrope |

\* Anton/Bebas/Oswald ALL CAPS white is the Jackie look: avoid it as the main caption face.

## 5. Uniqueness check (must pass before editing)

Compare the new guide with every entry in `reserved-styles.json` on these 7 points:
caption font, caption case, accent colour and treatment, caption animation, graphics family,
hook format, signature move.

- It **passes** if it differs from each reserved style on at least **5 of 7** points.
- Write the comparison as a small table at the bottom of the guide (point / reserved / new /
  different?). If it fails, change the weakest points and check again.
- Also compare with other prospects' guides in `styles/`: two prospects should not share a
  concept.

## 6. Storyboard for the user's review (required: no editing before approval)

Before cutting anything, show the user what the sample will look like:

1. Pull 6 real frames from the chosen bit with ffmpeg (hook moment, setup, a mid-story line,
   the punchline, the big laugh, the last line).
2. Mock each frame up as a finished 1080x1920 still in the new style: captions in the chosen font,
   size, position and colours with the real words from that moment, the emphasis rule applied, and
   the graphic motif planned for that beat. Build them as HTML or a Remotion still and screenshot
   them (Playwright / `npx remotion still`). Use the real footage, not generated images: it's free
   and shows the user exactly what they'll get. Never use paid image generation (Fish Audio) without
   an estimate and the user's approval.
3. Lay the 6 stills out on one storyboard sheet: frame number, timestamp, what happens there
   (caption, graphic, cut, sound cue) under each, the concept name and the 3 colour swatches on top,
   and one sheet section for the end card.
4. Save it as `styles/<prospect-slug>-storyboard.jpg`, send it to the user with a 3-line summary
   (concept, signature move, why it fits them), and **stop**. Wait for "approved" or their changes.
   Apply changes to the guide and re-send the storyboard until approved.

## 7. Edit the sample (only after the storyboard is approved)

Edit with the guide open: Remotion in `video/` for graphics-heavy looks, or ffmpeg cuts plus
burned-in ASS captions for simple ones. Render, make a 1 fps contact sheet, and check it against
the guide's don't-list before showing the user.

## 8. Keep the registry current

- New guide: `status: sample` in its own file. List it in the user's tracker next to the lead.
- Prospect becomes a paying client: add their style to `reserved-styles.json` with
  `status: owned` (copy the 7 points from their guide). From then on it is theirs.
- If `brenda` still has a `todo`, ask the user to describe her style or point to a delivered
  clip, and fill it in before the next uniqueness check.
