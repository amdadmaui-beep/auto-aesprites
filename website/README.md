# AVE Studio website

`mockup-v2/` is the approved-direction prototype (not final). Open it through a local server:

```bash
cd website/mockup-v2 && python3 -m http.server 8766
```

Then go to http://localhost:8766. All motion runs from one clock; `window.seek(t, scrollY)` paints a single frame,
which is how the preview video was rendered.

- Brand: ink `#0E0E0E`, off-white `#F3F2EE`, lime `#C8FF2E` (accent only).
- Type: Archivo Expanded (display, OFL, from `@fontsource-variable/archivo`), Inter Display, Instrument Serif italic, JetBrains Mono.
- Clips and stills are cut from `ave-promo/AVE_Studio_Promo_V3.mp4` (branch `claude/practical-faraday-7a7049`) as placeholders;
  swap in the real Drive footage for the build.
