---
name: jackie-edit-style
description: The user's signature "Jackie" editing style for stand-up comedy clips, taken from the Jackie Kashian "mother-in-law safe" edit. Use whenever the user says "Jackie style", "Jackie editing style", "edit it like Jackie", "our signature style", or asks for a vertical comedy/stand-up clip with captions and story graphics.
---

# Jackie editing style

The reference is a 70 s vertical stand-up clip of Jackie Kashian (the "mother-in-law's safe" bit).
Source on Google Drive (AVE Studio Showcase folder): file id `1XEKnqG1UIZsoweBMuMqLnF9qk2mf-LIf`
(`comedy_jackie_safe`). Download it with:
`curl -sL -o jackie.mp4 "https://drive.usercontent.google.com/download?id=1XEKnqG1UIZsoweBMuMqLnF9qk2mf-LIf&export=download&confirm=t"`

Look at `reference/key-moments.jpg` and the two `reference/timeline-*.jpg` sheets (one frame
per second, timestamps burned in) before editing. Match them.

In one line: **clean, punchy captions that read the joke for you, a lime accent on the words that
matter, and small "story graphics" that illustrate the bit. No flashy transitions.**

## Format

- 1080x1920 vertical, 23.976 or 30 fps, H.264, about 60–75 s (one complete bit, setup to final laugh).
- Loudness -14 LUFS integrated. Keep the room: laughter and room tone stay in, no music bed
  under the talking, no silence gaps.

## Framing: three shot sizes, hard cuts only

| Section | Shot | Reference |
|---|---|---|
| Hook / setup | **Wide**: full body, curtain and stage visible | 0–9 s |
| The story | **Medium close-up**: chest up, a punch-in on the same camera | 9–48 s |
| Big punchline laugh | **Back to wide**: give the laugh room, hold about 5 s | 48–53 s |
| Final act / tag | **Close-up**: tighter than the MCU | 53 s to end |

- Cut on a laugh or right after a punchline, never mid-sentence. Plain cuts: no zoom
  transitions, whip pans, shakes or flashes.
- Keep the speaker's face in the top third; captions sit over the chest.

## Captions (the core of the style)

- **ALL CAPS**, condensed bold sans (Bebas Neue / Oswald SemiBold / Anton look), white,
  soft dark drop shadow, no box.
- Centred horizontally, block centred at about **62–70 % of frame height** (y ≈ 1190–1370 px).
- 1–2 lines, 3–7 words per caption, phrase by phrase in time with speech. Keep punctuation,
  commas, ellipses and quote marks for dialogue: `AND CHRIS GOES, "OH MY GOSH,"`.
- **Lime accent `#C8F82C`** (≈ rgb 200, 248, 44) on the one key word: names, places, numbers,
  the punchline word (`DELAWARE,`, `SAFE`, `$3,000`). Never more than one accent per caption.
- Numbers and punchlines go **bigger**: the key word is 2–3x the caption size on its own line
  (`THEY ALSO HAD` / big lime `$3,000` / `IN $2 BILLS.`).
- Stage directions and asides are **dim grey** at reduced opacity: `THEN THERE WAS A PAUSE.`
- Captions cut in with a short fade (about 3 frames). No bouncing word-by-word karaoke.

## Story graphics (one every 5–10 s, always thin lime line art)

Small, flat, thin-stroke lime graphics that illustrate the exact thing being said, placed
near the caption and never covering the face:

- **Hook title** (first 3 s), left-aligned over the wide shot: tiny letter-spaced kicker
  (`POSITIVE MOTHER-IN-LAW JOKES`), then a 3-line title with the topic word in lime and larger
  (`WHEN MY` / `MOTHER-IN-LAW` / `MOVED IN...`), typed on with a cursor.
- **Counter tag**: small lime outlined box above the caption that ticks (`DAY 2` -> `DAY 4`)
  when time passes in the story.
- **Circle highlight**: dashed lime ring around a key word (`SAFE`).
- **Data grid**: e.g. 50 small circles with state codes, one dashed empty slot, plus a lime
  `MISSING` tag, for "they're missing Delaware".
- **Count-up number**: `$2,934` rolling up to `$3,000`, with a tiny footnote line
  (`(1,500 BILLS ≈ 6.5 IN.)`) and a thin vertical stack graphic beside it.
- **Boxed punchline**: the punch word in a hand-drawn, slightly jittering lime box (`LAND.`),
  held over the wide laugh shot.
- **Dial / echo**: a combination-lock dial ring with tick numbers behind the word, and the word
  stacking 1 -> 3 times (`SAFE` / `SAFE` / `SAFE`) as the speaker repeats it.

## End card (last ~1.5 s)

Freeze or blur the last frame, then centre the handle `@JACKIEKASHIAN` (white, condensed,
thin lime underline) with a tiny lime line under it (`ALTER-KASHIAN · STREAMING NOW`).
Swap in the comedian's own handle and current special.

## Sound

- Optional light SFX only on graphics (a soft click on a counter tick, a whoosh or pop on the
  boxed punchline). Use `video/public/sfx/` (`saas-ui-sfx` clicks, `trending-sfx` pops).
  Keep them quiet, under the voice, never on top of a laugh.

## Workflow

1. Get the transcript with word timings; mark the setup, each punchline and the big laugh.
2. Pick the cut points (the shot table above), then the 4–6 words that get lime and the
   4–6 graphics.
3. Build it in Remotion (`video/`): one composition at 1080x1920 with a caption track and
   a graphics track; or for simple jobs, ffmpeg cuts plus burned-in ASS captions.
4. Render, make a 1 fps contact sheet, and compare it side by side with
   `reference/timeline-*.jpg` before showing the user.
