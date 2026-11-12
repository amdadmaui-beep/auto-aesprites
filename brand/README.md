# AVE Studio brand

The live, browsable version: https://claude.ai/artifact/Nm1FQJurLDh5aQ6b5bND7A (private until shared). Fonts are in `ave-promo/film/fonts/`; the mascot poses are in `ave-promo/film/img/`.

AVE Studio is a video editing studio. We turn raw clips into short-form video that people actually watch: creators, podcasts, comedy, brands and real estate. Everything we publish should look like it came from one team.

## Voice

- Talk to the creator as "you", and speak as "we". Short, confident, a little playful. No jargon, no hype words ("revolutionary", "game-changing").
- Lines come in pairs: a setup and a payoff, with the payoff word emphasised. Use these as written:
  - "Got something worth *watching?*" / "Make sure it *looks* like it."
  - "You create. We make it *hit.*"
  - "Every frame, *on purpose.*" (our tagline)
- The call to action is always a direct message with one word in quotes: DM "SAMPLE" (or "EDIT" for real estate). Follow it with "Get your first sample edit."
- Sentence case everywhere. Uppercase only for `label` and `screen-label` text.
- No emoji inside videos. In social captions, at most two.

## Colour

- The brand is **Ink, Paper and Lime**. Ink (`ink`) and Paper (`paper`) do the work; `lime` is the one accent and should cover no more than about a tenth of any frame.
- Default to the Ink theme: `text` on `surface`. Use the Paper theme for light, calm formats such as real estate and before/after.
- Put `lime` behind or under the single most important thing: the payoff word, a highlight bar, the progress line, the play mark, an end-card panel.
- Lime text only on `ink`. On Paper, lime is a fill with `on-accent` text on top.
- Greys are warm (`grey-300`, `grey-500`, `grey-700`). Never use a neutral or blue grey.
- Never add a second accent colour. The real estate reel's cream and gold drifted from the brand; future ones use Paper, Ink and Lime.

## Type

- **Inter Display** carries everything. Headlines are ExtraBold (`screen-hero`, `display`), tight, with negative tracking.
- **Instrument Serif Italic** marks one emphasised word per line: the payoff. Set it in `screen-emphasis`, in `lime` on Ink or `ink` on Paper. Never a whole sentence.
- **JetBrains Mono** is for labels, chips, timestamps and UI text inside the frame (`screen-label`, `label`), in uppercase with wide tracking.
- On-screen captions use `screen-caption`: 1–3 words at a time, in the safe area, never over a face.

## Logo

- The wordmark is **AVE**, set as one solid mark. Use the files in Logos: `ave-wordmark-black` on Paper, `ave-wordmark-paper` on Ink, and `ave-wordmark-lime` on Ink only for end cards.
- When the full name is needed, set "STUDIO" under the mark in `screen-label` or `label`, centred, letter-spaced.
- Give the mark clear space of at least its own height on every side. Don't stretch it, outline it, add effects to it, or put it on a busy image without a plate.

## Mascot

- The cat in Mascot is our host. It appears in promos and end cards, never in client work.
- Uniform scale only: never stretch, warp or mirror a pose. Change poses only while the cat is hidden (a cut, a panel wipe), and never show two poses at once.
- The lime bandana carries the Λ mark. Keep it visible.

## Layout and shapes

- Video is built at 1080×1920 for vertical and 1920×1080 for wide. Keep `space-6` clear top and bottom, and `space-5` at the sides, for platform UI.
- Cards and video panels: `radius-md`, `surface-raised` or the footage itself, with `shadow-card` when they float on a backdrop.
- Chips and CTAs are pills (`radius-pill`).
- Spacing follows the scale: `space-1` to `space-6`. Don't invent in-between values.

## Motion

- Every cut lands on the music: on a beat, a drop or a hit. Map the track first, then edit.
- Prefer ease-out motion (things arrive fast and settle). A soft push-in keeps held shots alive; nothing should freeze dead.
- Our transitions: a lime panel wipe, a blur and scale kick on the cut, a box reveal, a circle reveal, vertical panel builds and diagonal shards. Use at most one showy transition per eight beats.
- Add motion blur to fast moves.

## Sound

- One sound per meaningful change on screen. If nothing changes, add no sound.
- Our palette is creamy and soft: low, round bloops, warm thocks, a ding for confirmations, and airy whooshes. No harsh clicks and no paper-tear sounds.
- Music leads. Sound effects sit on top, and the music ducks only slightly under them.
- Master to −14 LUFS, −1 dBTP.

## Formats we use

| Format | Theme | Notes |
| --- | --- | --- |
| Promo / spec ad | Ink | Hook, then range, then payoff, then end card with the mascot and DM "SAMPLE". |
| Talking-head reel | Ink or footage | `screen-caption` captions, one `screen-emphasis` payoff word per line, lime highlight bar. |
| Real estate before/after | Paper | "Before" chip on `surface-raised`, "After" chip on `ink`, footage cards with `radius-md`; the CTA is DM "EDIT". |
| End card | Ink | `ave-wordmark-paper` or `ave-wordmark-lime`, the tagline, then the CTA, held 1.5 seconds. |
