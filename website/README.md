# AVE Studio website

`mockup-v6/` is the current prototype: black and off-white sections alternating as stacked cards, crossing brand tapes, plus everything in v5.
`mockup-v5/` was the all-dark version: HUD callouts, mascot-through-type section, stacked-word services, hanging badge contact.
`mockup-v4/` was the previous prototype (v2 hero, 3D raw-to-vertical scene, Notion/SaaS section, 3D work carousel, services, FAQ, CTA, chrome-logo footer).
`mockup-v3/` is the first scroll-driven 3D page (Three.js 0.170, `lib/`).
`mockup-v2/` is the earlier 2D version. Open it through a local server:

```bash
cd website/mockup-v6 && python3 -m http.server 8766
```

Then go to http://localhost:8766. All motion runs from one clock; `window.seek(t, scrollY)` paints a single frame,
which is how the preview video was rendered.

- Brand: ink `#0E0E0E`, off-white `#F3F2EE`, lime `#C8FF2E` (accent only).
- Type: Archivo Expanded (display, OFL, from `@fontsource-variable/archivo`), Inter Display, Instrument Serif italic, JetBrains Mono.
- Clips and stills are cut from `ave-promo/AVE_Studio_Promo_V3.mp4` (branch `claude/practical-faraday-7a7049`) as placeholders;
  swap in the real Drive footage for the build.

`references/` holds the Pinterest boards (numbers 1–32) used to steer the design; the user picked 6, 7, 17, 23 and 32.
