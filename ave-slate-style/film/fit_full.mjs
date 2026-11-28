// Fit phone pose + lens (perspective) per frame, 1.20-3.37 s at 30 fps: whole-frame luminance match (+ avatar centre when tracked),
// with a smoothness term tying each frame to the previous one.
import { createRequire } from 'module'; import fs from 'fs'; import path from 'path';
const require = createRequire(import.meta.url);
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const { PNG } = require(path.resolve('../../.claude/skills/reanimate/scripts/node_modules/pngjs'));
const W = 60, H = 107;
const pool = (png) => { const o = new Float32Array(W * H), cnt = new Float32Array(W * H);
  for (let y = 0; y < png.height; y++) for (let x = 0; x < png.width; x++) { const i = (y * png.width + x) * 4; const l = .3 * png.data[i] + .59 * png.data[i + 1] + .11 * png.data[i + 2];
    const j = Math.min(H - 1, Math.floor(y * H / png.height)) * W + Math.min(W - 1, Math.floor(x * W / png.width)); o[j] += l; cnt[j]++; }
  for (let j = 0; j < o.length; j++) o[j] /= cnt[j]; return o; };
const prep = (a) => { // local contrast: subtract a blurred copy, so layout edges matter more than absolute colour
  const b = new Float32Array(a.length); for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) { let s = 0, n = 0;
    for (let dy = -4; dy <= 4; dy++) for (let dx = -4; dx <= 4; dx++) { const yy = y + dy, xx = x + dx; if (yy < 0 || xx < 0 || yy >= H || xx >= W) continue; s += a[yy * W + xx]; n++; } b[y * W + x] = a[y * W + x] - s / n; }
  let m = 0; for (const v of b) m += v * v; m = Math.sqrt(m / b.length) + 1e-6; return b.map(v => v / m); };
const track = Object.fromEntries(JSON.parse(fs.readFileSync('build/fit/avatar_track.json')).filter(Boolean).map(r => [r.t.toFixed(3), r]));
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 720, height: 1280 }, deviceScaleFactor: .25 });
await page.goto('file://' + path.resolve('index.html')); await page.evaluate(() => window.ready);
await page.evaluate(() => { const av = document.querySelector('#avatar'); const m = document.createElement('i'); m.id = 'mC'; m.style.cssText = 'position:absolute;left:85px;top:85px;width:1px;height:1px;display:block'; av.appendChild(m); });
const N = fs.readdirSync('build/fit2').filter(f => f.startsWith('ref_')).length;
const out = []; let prev = null;
for (let k = 0; k < N; k++) {
  const t = +(1.2 + k / 30).toFixed(3); if (t > 3.37) break;
  const ref = prep(pool(PNG.sync.read(fs.readFileSync(`build/fit2/ref_${String(k + 1).padStart(3, '0')}.png`))));
  await page.evaluate(t => window.seek(t), t);
  const av = t >= 2.29 ? track[t.toFixed(3)] : null;
  const ry = t < 2.95 ? 360 : t < 3.3 ? 360 + 22 * Math.sin(Math.PI * (t - 2.95) / .35) : 360;
  const f = async (q) => { const m = await page.evaluate(([q, ry]) => { window.posePhone(130, 279, q[0], q[1], q[2], q[3], ry, q[4], q[5]);
      const r = document.getElementById('mC').getBoundingClientRect(); return [r.left, r.top]; }, [q, ry]);
    const img = prep(pool(PNG.sync.read(await page.screenshot({ type: 'png' }))));
    let e = 0; for (let i = 0; i < img.length; i++) e += (img[i] - ref[i]) ** 2; e /= img.length;
    if (av) e += ((m[0] - av.cx) ** 2 + (m[1] - av.cy) ** 2) / 4000;
    if (prev) { const sc = [1 / 60, 1 / 60, 3 / prev[2], 1 / 6, 1 / 6, 1 / 300]; for (let d = 0; d < 6; d++) e += .02 * ((q[d] - prev[d]) * sc[d]) ** 2; }
    return e; };
  let init = prev ? prev.slice() : null;
  if (!init) { const kk = await page.evaluate(t => window.phoneAt(t), t); init = [kk[3] + (130 - kk[1]) * kk[5], kk[4] + (279 - kk[2]) * kk[5] * .8, kk[5], kk[6], kk[8], 1500]; }
  let best = init, bs = await f(best), step = [36, 36, best[2] * .1, 6, 6, 250];
  for (let it = 0; it < 10; it++) { let imp = false;
    for (let d = 0; d < 6; d++) for (const s of [1, -1]) { const x = best.slice(); x[d] += s * step[d]; if (x[2] < .2 || x[5] < 250 || x[5] > 3000) continue; const v = await f(x); if (v < bs) { bs = v; best = x; imp = true; } }
    if (!imp) step = step.map(v => v / 2); }
  prev = best; out.push([t, ...best.map(v => +v.toFixed(3)), ry]);
  console.log(t.toFixed(3), bs.toFixed(3), best.map(v => v.toFixed(1)).join(' '));
}
fs.writeFileSync('build/fit/full_fit.json', JSON.stringify(out)); await browser.close();
