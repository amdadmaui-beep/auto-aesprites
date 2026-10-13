// Shared timeline: read by index.html (picture) and audio.py (sound). Seconds.
window.CUES = {
  dur: 18.0, fps: 60, bpm: 120,
  S1: 0.0, S2: 1.5, S3: 3.5, S4: 5.5, S5: 8.0, S6: 11.5, S7: 13.0, S8: 15.75,
  // 1 · mascot intro
  catIn: 0.04, land: 0.70, tailFlick: 0.84, blink1: 1.00, glance: 1.16, micro: 1.20,
  // 2 · hook
  got: 1.50, worth: 2.55, watching: 2.85, tilt: 2.90, hookOut: 3.40,
  // 3 · service cards
  card1: 3.50, card2: 4.20, card3: 4.90,
  // 4 · raw -> AVE edit
  phoneIn: 5.50, line1: 5.62, tap: 6.00, frame: 6.04, subs: 6.52, hiword: 6.86,
  motion: 7.02, wave: 7.22, visual: 7.42, line2: 7.28, aveEdit: 7.74,
  // 5 · dashboard pipeline
  dashIn: 8.00, scrub: 8.14, clipSel: 8.60, chipFly: 8.74, capsIn: 9.22,
  motionOn: 9.88, soundOn: 10.16, tagImpact: 10.26, tagClick: 10.40, tagWhoosh: 10.54,
  visualOn: 10.58, readyIn: 10.80, plat1: 10.96, plat2: 11.08, plat3: 11.20, ready: 11.32,
  // 6 · range
  p1: 11.50, p1punch: 11.72, p2: 12.00, p2switch: 12.24, p3: 12.50, p3click: 12.76,
  // 7 · brand statement
  youCreate: 13.10, weMake: 14.49, hit: 15.25,
  // 8 · end card
  endIn: 15.75, cta: 16.22, wave1: 16.30, blinkEnd: 17.40
};
