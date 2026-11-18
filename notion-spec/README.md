# Notion Agents spec spot (31s, 16:9)

A spec commercial for Notion's AI agents, modelled on the beat structure of the client's reference (a monday.com agents promo): meeting chaos → status-update chat bubbles → "Nobody doing." → AI prompt → pick an agent → Read / Flag / Push → results → "The meeting? Cancelled." → end card. Picture is built as code with real assets: the official Notion mark, real (stock) people cut out with rembg, Notion-style pages with photo covers and emoji icons. Music and sound design are original. Rendered with 2-sample motion blur.

## Script (voiceover, two voices like the reference)
| t (s) | voice | line |
|---|---|---|
| 0.35 | Sarah | *(chuckle)* Remember status meetings? |
| 2.85 | Sarah | Everyone reporting. |
| 4.75 | Sarah | Nobody doing. |
| 6.50 | Jane Perry | Now Notion gives your team agents. |
| 9.05 | Sarah | Pick the one you need. |
| 10.75 | Jane Perry | They read every doc, flag what's stuck, and push it forward. |
| 14.40 | Jane Perry | Three risks flagged. |
| 16.30 | Sarah | Launch plan, drafted. |
| 18.70 | Sarah | Working on it. Done, done, done. |
| 22.40 | Sarah | *(chuckle)* The meeting? |
| 24.30 | Sarah | Cancelled. |
| 26.40 | Jane Perry | Notion. Less talk. More done. |

Lines were generated with Fish Audio (`vo/ids.txt` lists each task id), trimmed of silence, and placed by `cues.js`.

## Files
| Path | What it is |
|---|---|
| `vo/` | Voiceover lines (mp3 from Fish, trimmed wav used in the mix). |
| `film/cues.js` | The single timeline. Picture and sound both read it. |
| `film/index.html` | The film. `window.seek(t)` paints any frame as a pure function of time. |
| `film/brand/` | Official Notion mark (`notion-mark.svg`, from Wikimedia Commons; `notion-mark-sticker.svg`, from notion.com's header). |
| `film/img/` | Cast cut-outs (`img/people/` holds the Unsplash originals `pNN_<photo id>.jpg` and raw cut-outs) and page covers (`img/covers/`, Unsplash). Unsplash License: free for commercial use. |
| `film/audio.py` | Original score (104 BPM, F major: keys, plucks, bass, drums, pad, end-chord bells), synthesized UI sound design, VO placement and ducking. |
| `film/render.mjs` | Headless Chromium → frames → H.264. `--times=1,2.5` writes stills instead. |
| `Notion_Agents_Spec_16x9.mp4` | Final: 1920×1080, 60 fps, H.264 CRF 16, AAC 320k, −14 LUFS. |

## Rebuild
```bash
cd film
pip install numpy scipy soundfile
python audio.py                                   # build/music.wav, sfx.wav, vo.wav, mix_raw.wav
node render.mjs --video=build/video.mp4           # ~20 min (2 sub-frames per frame; --sub=1 for a fast draft)
ffmpeg -i build/mix_raw.wav -af "volume=-6dB,alimiter=limit=0.89:attack=2:release=60,loudnorm=I=-14:TP=-1:LRA=9" -ar 48000 build/mix.wav
ffmpeg -i build/video.mp4 -i build/mix.wav -c:v copy -c:a aac -b:a 320k -shortest ../Notion_Agents_Spec_16x9.mp4
```

## Notes
- UI is an illustrative recreation in a Notion-like style, not screen recordings. Names, numbers and pages are sample content.
- The end card uses the official mark; the "Notion" wordmark is set in Inter Bold (Notion's site typeface) since notion.com does not serve a standalone wordmark file.
- People were going to be 3D renders like the reference, but the Fish free plan hit its daily image limit; the real-photo cast can be swapped for 3D characters by replacing the PNGs in `film/img/` (same names).
- Typefaces: Inter Display (UI/type), Instrument Serif Italic (payoff word).
