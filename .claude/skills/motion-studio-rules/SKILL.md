---
name: "motion-studio-rules"
description: "Use for any motion film, promo video, product ad, kinetic-type piece or animated explainer: the studio's render contract, look rules, sound rules and score-and-fix loop."
---

# Motion studio rules

These are the studio's standing rules. They apply to every film unless the brief explicitly overrides one.

## Render contract
- Every film is a pure function of time: `window.seek(t)` paints frame t.
- No CSS transitions, no setTimeout, no requestAnimationFrame in render mode,
  no state carried between frames. Seeded noise only (mulberry32), never Math.random.
- Render with `node render.mjs`, encode H.264 yuv420p, CRF 16.

## Look
- Banned defaults: centered title on gradient, everything fading in,
  corner labels and frame borders, glow on UI chrome, generic particle bursts.
- One display face, one UI face. One accent color unless the brief says otherwise.
- Every 2 to 4 seconds something new must happen on screen.

## Sound
- Score and SFX are synthesized in code unless a track is supplied.
- Place hits on the measured beat grid (beats.json). Loudness -14 LUFS.

## Loop before you show me anything
1. Render one frame per beat as a contact sheet and LOOK at it.
2. Score it 1-10 on: hook in first 2s, readability at phone size,
   motion quality, variety, brand accuracy, sound sync.
3. Fix the 3 worst problems. Repeat until every score is 8+.
4. Only then do the full render.

---

# How to apply (reference)

## Film page skeleton
```js
// Pure function of time. No timers, no rAF in render mode, no carried state.
function mulberry32(a) {
  return function () {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const noise = (seed) => mulberry32(seed)(); // derive per-element seeds from ids, never from call order

window.seek = async (t) => {
  // compute every element's state from t alone, paint it, await fonts/images if needed
};
```
Preview mode may drive `seek` from rAF, but render mode never does.

## render.mjs (shape)
- Launch headless Chromium (Playwright or Puppeteer), load the film page, `await document.fonts.ready`.
- For frame i in 0..N-1: `await page.evaluate(t => window.seek(t), i / fps)`, screenshot to PNG (or pipe raw frames).
- Encode: `ffmpeg -framerate <fps> -i frames/%05d.png -i score.wav -c:v libx264 -pix_fmt yuv420p -crf 16 -c:a aac -b:a 320k -shortest out.mp4`.

## Contact sheet: one frame per beat, at phone size
Use the beat grid from beats.json. For a constant tempo, frames per beat = fps * 60 / bpm (120 BPM at 30 fps = 15):
```
ffmpeg -i out.mp4 -vf "select='not(mod(n\,15))',scale=384:216,tile=10x6:padding=4" -vsync 0 sheet_%d.png
```
384 px wide approximates how a 1080p film reads on a phone, so this sheet is also the readability test. When the full film isn't rendered yet, render just the beat frames with `node render.mjs --frames=<list>`.

## beats.json
Measure it from the synthesized score: detect kick (or main percussion) onsets, then store
`{ "bpm": 120, "beats": [0.0, 0.5, 1.0, ...], "downbeats": [0.0, 2.0, ...] }`.
Scene changes, cuts, text hits and impacts snap to entries in `beats`. Typing and UI micro-clicks may follow on-screen action but stay under the music.

## Loudness
Measure: `ffmpeg -i out.mp4 -af ebur128=peak=true -f null -` (read `I:` in the summary).
Normalize the score to -14 LUFS integrated, e.g. `ffmpeg -i score.wav -af loudnorm=I=-14:TP=-1:LRA=11 score_norm.wav` (two-pass for accuracy).

## Scoring notes
- Report the six scores in a table with one line of evidence each, taken from the contact sheet.
- Fix the three lowest, re-render the beat frames only, re-score. Repeat until every score is 8 or higher.
- Don't show the person a draft, a still or a full render before the loop passes, unless they ask for a progress check.