// AVE "more heat" reel — timing matched to the reference cut (cuts, hits and gaps), 9.25s.
window.CUES = {
  dur: 9.25, fps: 60,
  // 1 · heat
  flash: 0.23, icon: 0.10, roll: 0.12, rollEnd: 0.45, cap: 0.20, warm: 0.75, hot: 1.5, build1: 1.52,
  // 2 · cards: hard colour cuts
  card1: 1.70, title1: 2.95, build2: 3.57, card2: 3.733, build3: 4.30, card3: 4.40, card4: 4.90, build5: 5.63,
  // 3 · white
  white: 5.867, slam: 5.98, purpose: 6.25, stop: 6.40,
  // 4 · lockup
  lock: 6.70, logo: 6.75, studio: 6.95, rule: 7.05, dm: 7.25, type: 7.80, send: 8.35, sub: 8.45,
  // clip cuts inside the card (from the reference"s frame-by-frame changes)
  SHOTS: [[1.70,"flash_kt",0.3,1],[1.833,"feed_kt",1.0,0],[1.90,"flash_kt",0.5,1],[2.00,"feed_roast",1.2,0],[2.20,"flash_kt",0.8,1],
          [2.933,"flash_kt",1.45,0],[3.00,"feed_conor",2.0,0],[3.067,"flash_kt",1.5,0],[3.133,"feed_jackie",1.0,0],[3.267,"card_comedy",1.4,0],[3.433,"flash_kt",1.6,0],
          [3.733,"flash_sp",0.1,0],[4.167,"feed_sp",1.0,0],[4.267,"card_podcast",1.5,0],
          [4.40,"mp_edit",2.2,0],[4.70,"longform",2.0,0],[4.833,"mp_edit",3.2,0],
          [4.90,"hero_motion",2.4,0],[5.267,"card_motion",2.0,0],[5.467,"hero_motion",3.3,0]],
  // sub/kick hits measured from the reference (the ribbon and the glow pulse on these)
  BEATS: [0.05,0.17,0.27,0.51,0.60,0.71,0.80,0.94,1.06,1.19,1.29,1.39,1.50,1.70,1.79,1.96,2.08,2.29,2.44,2.56,2.66,2.84,2.94,3.10,3.22,3.35,3.50,3.66,3.83,3.96,4.06,4.20,4.41,4.52,4.66,4.91,5.06,5.32,5.46,5.63,5.72,5.84,5.96,6.05,6.18,6.32,6.44,6.54,6.68,6.82,7.08,7.17,7.30,7.42,7.52,7.68,7.78,7.88,8.01,8.25,8.50,8.60],
  HATS: [0.04,0.51,1.39,1.64,2.97,3.11,3.76,4.07,4.71,5.27,5.46,5.68,5.89,6.46,6.56,6.73,6.84,6.94,7.17,7.32,7.54,8.01,8.17,8.39,8.49]
};
