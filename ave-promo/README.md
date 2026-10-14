# AVE Studio — mascot promo

- `AVE_Studio_Promo_V3.mp4` — current cut: 32s, 1920×1080, 60fps, Jane Perry VO, real AVE footage, original V3 score.
- `AVE_Studio_Promo_V2.mp4` — V2, source in `film/v2/`.
- `AVE_Studio_Promo.mp4` — V1 (18s), source in `film/v1/`.

Footage frames are not committed: run `tools/extract_clips.sh` to rebuild `film/clips/` from the AVE Studio Showcase Drive folder. Drop the licensed music track at `film/build/music.wav` (48 kHz) and re-run `film/audio.py` — it replaces the original score (`film/score_v3.py`) automatically.

## Structure

| Path | What it is |
| --- | --- |
| `film/cues.js` | The single timeline. Picture and sound both read it, so moving a cue moves its animation and its sound together. |
| `film/index.html` | The film. `window.seek(t)` paints any frame as a pure function of time. Open `index.html?play` in a browser to preview, `?t=12.3` for one frame. |
| `film/render.mjs` | Headless Chromium → PNG frames → H.264 (CRF 16, yuv420p). |
| `film/audio.py` | Sound design + voiceover placement, ducks music under voice, writes `build/mix_raw.wav`. |
| `film/score_v3.py` | The original score: 120 BPM, D dorian; layered kick, roomy clap, swung hats, funky 16th bass with slides, FM bell motif with ping-pong delay, offbeat stabs, glitch stutters. |
| `film/img/` | Mascot poses (cut out, edge-cleaned, lime Λ mark printed on the bandana). |
| `vo/` | V1 male voiceover lines (Fish Audio, voice "Slax"). |
| `vo2/` | V2/V3 voiceover lines (Jane Perry). |
| `tools/` | Cut-out (`cutout.py`, BiRefNet via rembg) and asset prep (`prep.py`). |

## Rebuild

```bash
cd film
python audio.py                      # needs numpy + scipy; writes build/mix_raw.wav
# normalize to -14 LUFS / -1 dBTP (two-pass loudnorm), then:
node render.mjs --video=build/video.mp4
ffmpeg -i build/video.mp4 -i build/mix.wav -c:v copy -c:a aac -b:a 320k -shortest AVE_Studio_Promo_V3.mp4
```

Serve nothing manually: `render.mjs` starts its own local server. It uses the system Playwright Chromium with SwiftShader WebGL (the cat rig is a WebGL shader: head tilt, tail flick, blink, paw tap and wave are warps of the still poses).

## Scenes (V3)

The mascot never stretches or warps: placement is uniform scale only, pose changes always happen fully occluded (motion blur dash, a lime panel, the end-card flip), and two poses are never on screen together.

1. Hook (0–4s) — the cat lands, looks at the viewer, blinks, notices the type and turns to it; "Got something worth *watching?*" / "Make sure it *looks* like it."
2. Who we work with (4–7.45s) — the cat raises its paw and triggers each card (Comedy / Podcasts / Creators), then taps Podcasts.
3. Clip selection (7.45–11.6s) — card 2 expands into the dashboard's CLIP SELECTION tile; long-form footage scrubs, a moment is found, selected, and the clip chip flies to CAPTIONS while a watcher cat follows the playhead.
4. The AVE edit (11.6–16.6s) — CAPTIONS (Mind Pump raw → reframed → captioned edit), then MOTION, VISUAL STORY, SOUND (Impact / Click / Whoosh) and READY TO POST run in order; the operator cat types and taps along.
5. Posted → watched (16.6–20.8s) — the READY thumbnail becomes the centre phone of a feed; everything recedes, then a big lime *watched.*
6. Range (20.8–25.3s) — Comedy and Podcast flashes, then the Motion lab: hero edit, transform handles, motion path, caption layer, keyframes and waveform; the cat drags a keyframe and taps the waveform.
7. Payoff (25.3–29.3s) — black, "You create." pause "We make it *hit.*"; music drops out, then the impact.
8. End card (29.3–32s) — a panel flips over the black scene, then logo, "Every frame, *on purpose.*", DM "SAMPLE", "Get your first sample edit." and the waving cat, held for ~1.5s.
