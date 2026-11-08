// 9:16 reframe: the 1920×1080 composition is filmed by a virtual camera inside a 1080×1920 page.
// Each entry: [tStart, tEnd, cx, cy, w] → by tEnd the camera frames a window w px wide centred on (cx, cy);
// tStart === tEnd is a cut, otherwise it is a smooth move from wherever the camera was.
const VW = 1080, VH = 1920;
const VK = [
  [0, 0, 960, 540, 1150],          // IDEAS.
  [.578, .578, 960, 540, 1640],    // INTO REALITY.
  [1.40, 1.40, 1150, 560, 1300], [1.45, 2.55, 1260, 600, 1150],   // ⌘K macro, drifting toward the keys
  [2.60, 2.60, 880, 520, 1260], [4.20, 5.38, 960, 520, 860],      // code locks, then the rush into the ember
  [5.40, 5.40, 960, 520, 950],                                    // ember
  [6.90, 6.90, 960, 520, 1080], [7.00, 8.40, 960, 520, 940],      // detonation → cube
  [8.49, 8.49, 960, 540, 1500], [8.55, 10.40, 960, 540, 1380],    // orbit
  [10.47, 10.47, 760, 540, 1400],                                 // MEET CURSOR.
  [12.45, 12.45, 1290, 470, 1150], [12.50, 13.36, 1345, 470, 1150],  // follow the caret as it types
                                  // typing macro
  [13.44, 13.44, 900, 500, 1300],                                 // ghost suggestion
  [14.03, 14.03, 520, 580, 980], [14.52, 14.80, 1340, 540, 1000], // Tab key → the accepted code
  [14.82, 14.82, 780, 500, 1300],                                 // slabs
  [16.40, 16.40, 720, 580, 1300],                                 // LESS TYPING. MORE BUILDING.
  [18.38, 18.38, 980, 640, 1100],                                // prompt
  [19.86, 19.86, 960, 520, 1720],                                 // files fan out
  [20.75, 20.75, 1040, 500, 1050],                                // diff montage (active card)
  [23.13, 23.13, 510, 520, 950], [23.55, 23.85, 1410, 520, 950],  // terminal → agent steps, in time for the ✓
  [24.31, 24.31, 480, 520, 950], [24.40, 24.66, 1415, 540, 950],  // code → browser as components land
  [25.70, 25.70, 900, 560, 1660], [26.30, 26.65, 960, 540, 1720], // ONE PROMPT. / preview grows
  [26.69, 26.69, 960, 560, 1500],                                 // explode
  [27.87, 27.87, 960, 560, 1500], [29.20, 29.80, 960, 540, 1780], // reconstruct → flat dashboard
  [30.64, 30.64, 960, 560, 1700], [31.00, 32.60, 870, 600, 1580], // pull back into the editor, FROM CODE. TO CREATION.
  [33.02, 33.02, 960, 520, 1850], [33.30, 33.90, 400, 520, 720],  // three agents → dolly along them as they finish
  [33.95, 34.70, 1520, 520, 720], [34.80, 35.40, 960, 520, 900],  //   … card 1 → card 3, then the fold to centre
  [36.18, 36.18, 960, 520, 1000],                                 // ember
  [36.97, 36.97, 960, 560, 1000], [37.00, 39.30, 960, 560, 930],  // lockup, slow push
];
const vease = x => x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;
function vframe(t) {
  let cur = VK[0].slice(2), from = cur;
  for (const [a, b, cx, cy, w] of VK) {
    if (t < a) break;
    const target = [cx, cy, w];
    if (b <= a || t >= b) { from = target; cur = target; continue; }
    const u = vease((t - a) / (b - a)); cur = from.map((v, i) => v + (target[i] - v) * u); break;
  }
  return cur;
}
function vcam(t) {
  const [cx, cy, w] = vframe(t), s = VW / w;
  window.VSTAGE.style.transform = `translate(${VW / 2 - cx * s}px, ${VH / 2 - cy * s}px) scale(${s})`;
  // the page continues the shot's own background above and below the composition
  const bg = t < C.sh4 ? '#000' : t < C.sh1 ? '#F7F7F4' : '#0E0D09';
  window.VPAGE.style.background = bg;
}
