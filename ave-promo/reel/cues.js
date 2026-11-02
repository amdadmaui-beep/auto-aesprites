// AVE "more heat" reel — paced to music draft A (96 BPM, bar = 2.5s), 15s.
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
  SHOTS: [[2.5,"flash_kt",0.3,1],[3.1,"feed_kt",1.0,1],[3.6,"flash_kt",1.45,0],[4.0,"feed_roast",1.2,0],
          [4.375,"flash_sp",0.1,0],[5.2,"feed_sp",1.0,0],[5.75,"card_podcast",1.5,0],
          [6.25,"mp_edit",2.2,0],[7.3,"mp_edit",4.0,0],
          [8.125,"hero_motion",2.4,0],[9.0,"card_motion",2.0,0],[9.5,"hero_motion",3.3,0]],
  BEATS: [2.5, 3.594, 4.062, 5.0, 6.094, 6.562, 7.5, 8.594, 9.062, 9.688, 10.0, 11.25, 12.5, 14.0625]
};
