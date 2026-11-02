// AVE "more heat" reel — paced on a 96 BPM grid (bar = 2.5s), voice + sound design only, 15s.
window.CUES = {
  dur: 15.0, fps: 60, bpm: 96,
  // 1 · heat (bar 1)
  flash: 0.35, icon: 0.2, roll: 0.9, rollEnd: 1.7, cap: 0.75, warm: 1.3, hot: 2.3, build1: 2.15,
  // 2 · cards (bars 2–4), one card every three beats
  card1: 2.5, title1: 3.6, build2: 4.1, card2: 4.375, build3: 5.95, card3: 6.25, card4: 8.125, build5: 9.6,
  // 3 · breakdown (bar 5)
  white: 10.0, slam: 10.15, purpose: 10.65, stop: 10.9,
  // 4 · resolve (bar 6)
  lock: 12.5, logo: 12.55, studio: 12.85, rule: 13.0, dm: 12.85, type: 13.1, send: 13.9, sub: 14.05,
  SHOTS: [[2.5,"s01",0,1],[3.05,"s15",0,0],[3.6,"s03",0,0],[4.0,"s14",0,0],
          [4.375,"s05",0,0],[5.0,"s06",0,0],[5.6,"s07",0,0],
          [6.25,"s08",0,0],[6.9,"s09",0,0],[7.5,"s10",0,0],
          [8.125,"s12",0,0],[8.9,"hero_motion",3.0,0]],
  BEATS: [2.5, 3.594, 4.062, 5.0, 6.094, 6.562, 7.5, 8.594, 9.062, 9.688, 10.0, 11.25, 12.5, 14.0625]
};
