# Motion Reel — 25 s, 1080p60

`reel.mp4` is a 25-second motion showreel, rendered entirely from code: every frame is `seek(t)`, a pure function of time. It uses no keyframes, no timers and no stock assets, and the score is synthesized too.

**Studio name:** change `STUDIO` in `film.js` (default `GEMINI`), or preview another name with `film.html?name=YOURSTUDIO`, then run `./make.sh`.

| time | scene |
|---|---|
| 0–2 s | WE MAKE THINGS MOVE. — kinetic hook, variable-weight type |
| 2–4 s | the period becomes a ball: timing, spacing, squash & stretch, onion skins |
| 4–6.5 s | graph editor: linear → ease out → ease in-out → overshoot → spring |
| 6.5–8.5 s | morph + stagger grid that collapses into baselines |
| 8.5–10.5 s | kinetic type rows: weight wave, width jumps, beat kicks; whip pan out |
| 10.5–12.5 s | 3D card ring stepping on the beat; front card flies into the lens |
| 12.5–14.5 s | parametric paths with trim, straightening into a chart baseline |
| 14.5–16.5 s | data: spring bars, sort, line chart, odometer roll |
| 16.5–18 s | generative Bauhaus tile system |
| 18–21 s | zoom out: the whole reel as a live 3×3 mosaic, shuffles, flips |
| 21–25 s | studio lockup; the ball rolls the rule and lands as the full stop |

## Build

```
npm install          # playwright 1.56.1 + fonts (Archivo variable, JetBrains Mono)
./make.sh            # synth.py -> beats.json -> render.mjs -> loudnorm (-14 LUFS) -> reel.mp4
node render.mjs --beats   # just the frames on the beat grid, for contact sheets
```

- `film.html` / `film.js`: the film (Canvas 2D). `?play` previews in real time and `?t=12.3` shows a single frame.
- `synth.py`: score and SFX (numpy only). Writes `beats.json`, which is measured from the kick stem.
- `render.mjs`: headless Chromium frame renderer that runs 4 pages in parallel.
