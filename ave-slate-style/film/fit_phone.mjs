// Fit the phone pose to every reference frame (15 fps, 0-4.27 s) by coordinate descent on a luminance match.
import { createRequire } from 'module'; import fs from 'fs'; import path from 'path';
const require = createRequire(import.meta.url);
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const { PNG } = require(path.resolve('../../.claude/skills/reanimate/scripts/node_modules/pngjs'));
const W = 45, H = 80;                       // compare on a 4x pooled grid of the 180x320 frames
const pool = (png) => { const o = new Float32Array(W * H); const f = png.width / W;
  for (let y = 0; y < png.height; y++) for (let x = 0; x < png.width; x++) { const i = (y * png.width + x) * 4; const l = .3 * png.data[i] + .59 * png.data[i + 1] + .11 * png.data[i + 2];
    o[Math.floor(y / f) * W + Math.floor(x / f)] += l / (f * f); } return o; };
const norm = (a) => { let m = 0, s = 0; for (const v of a) m += v; m /= a.length; for (const v of a) s += (v - m) ** 2; s = Math.sqrt(s / a.length) + 1e-6; return a.map(v => (v - m) / s); };
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 720, height: 1280 }, deviceScaleFactor: 0.25 });
await page.goto('file://' + path.resolve('index.html')); await page.evaluate(() => window.ready);
const N = fs.readdirSync('build/fit').filter(f => f.startsWith('ref_')).length;
const out = []; let prev = null;
for (let k = 0; k < N; k++) {
  const t = k / 15;
  const ref = norm(pool(PNG.sync.read(fs.readFileSync(`build/fit/ref_${String(k + 1).padStart(3, '0')}.png`))));
  await page.evaluate(t => window.seek(t), t);
  const key = await page.evaluate(t => window.phoneAt(t), t);   // [t,px,py,sx,sy,sc,rx,ry,rz]
  // express the prior key with the pivot at the phone centre
  let p = prev ? prev.slice() : null;
  if (!p) p = [key[3], key[4], key[5], key[6], key[7], key[8]];
  const P = [130, 279];
  const cand = [p, [key[3] + (130 - key[1]) * key[5], key[4] + (279 - key[2]) * key[5] * Math.cos(key[6] * Math.PI / 180), key[5], key[6], key[7], key[8]]];
  const score = async (q) => { await page.evaluate(([P, q]) => window.posePhone(P[0], P[1], ...q), [P, q]);
    const img = norm(pool(PNG.sync.read(await page.screenshot({ type: 'png' }))));
    let e = 0; for (let i = 0; i < img.length; i++) e += (img[i] - ref[i]) ** 2; return e / img.length; };
  let best = null, bs = 1e9; for (const c of cand) { const s = await score(c); if (s < bs) { bs = s; best = c.slice(); } }
  let step = [40, 40, Math.max(.05, best[2] * .12), 8, 14, 6];
  for (let round = 0; round < 6; round++) {
    let improved = false;
    for (let d = 0; d < 6; d++) for (const sgn of [1, -1]) {
      const q = best.slice(); q[d] += sgn * step[d]; if (d === 2 && q[2] < .05) continue;
      const s = await score(q); if (s < bs) { bs = s; best = q; improved = true; }
    }
    if (!improved) step = step.map(v => v / 2);
  }
  prev = best; out.push([+t.toFixed(3), 130, 279, ...best.map(v => +v.toFixed(3))]);
  console.log(k, t.toFixed(2), bs.toFixed(3), best.map(v => v.toFixed(1)).join(' '));
}
fs.writeFileSync('build/fit/phone_fit.json', JSON.stringify(out));
await browser.close();
