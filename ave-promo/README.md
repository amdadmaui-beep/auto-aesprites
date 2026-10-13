# AVE Studio — mascot promo (18s, 1920×1080, 60fps)

`AVE_Studio_Promo.mp4` is the finished film. Everything here rebuilds it.

## Structure

| Path | What it is |
| --- | --- |
| `film/cues.js` | The single timeline. Picture and sound both read it, so moving a cue moves its animation and its sound together. |
| `film/index.html` | The film. `window.seek(t)` paints any frame as a pure function of time. Open `index.html?play` in a browser to preview, `?t=12.3` for one frame. |
| `film/render.mjs` | Headless Chromium → PNG frames → H.264 (CRF 16, yuv420p). |
| `film/audio.py` | Synthesized score + SFX, places the voiceover, ducks music under voice, writes `build/mix_raw.wav` and `beats.json`. |
| `film/img/` | Mascot poses (cut out, edge-cleaned, lime Λ mark printed on the bandana). |
| `vo/` | Male voiceover lines (Fish Audio, voice "Slax"). |
| `tools/` | Cut-out (`cutout.py`, BiRefNet via rembg) and asset prep (`prep.py`). |

## Rebuild

```bash
cd film
python audio.py                      # needs numpy + scipy; writes build/mix_raw.wav
# normalize to -14 LUFS / -1 dBTP (two-pass loudnorm), then:
node render.mjs --video=build/video.mp4
ffmpeg -i build/video.mp4 -i build/mix.wav -c:v copy -c:a aac -b:a 320k -shortest AVE_Studio_Promo.mp4
```

Serve nothing manually: `render.mjs` starts its own local server. It uses the system Playwright Chromium with SwiftShader WebGL (the cat rig is a WebGL shader: head tilt, tail flick, blink, paw tap and wave are warps of the still poses).

## Scenes

1. Mascot intro (0–1.5s) — hop-in, blink, tail flick, glance; `// AVE STUDIO` types where the cat looks.
2. Hook (1.5–3.5s) — "Got something / worth *watching?*", lime marker under the accent word, curious head tilt.
3. Service cards (3.5–5.5s) — Comedy / Podcasts / Creators in staggered 3D; the cat presents them.
4. Raw → AVE EDIT (5.5–8s) — card 3's phone becomes the hero phone; the cat taps it and one continuous edit happens: framing, grade, captions, highlight, motion marks, waveform, B-roll card, label flips to AVE EDIT.
5. Dashboard (8–11.5s) — the edited phone shrinks into READY TO POST, then the pipeline runs tile to tile: clip select → captions → motion → sound (IMPACT / CLICK / WHOOSH) → visual story → READY ✓. The mascot is the operator tile.
6. Range (11.5–13s) — Protect the *punchline.* / Move the *conversation.* / Make ideas *move.*
7. Payoff (13–15.75s) — black, "You create. We make it *hit.*", controlled bass hit and camera push; the cat opens its eyes on "hit."
8. End card (15.75–18s) — the black frame closes into the `DM "SAMPLE"` pill; logo, tagline, services line, waving cat.
