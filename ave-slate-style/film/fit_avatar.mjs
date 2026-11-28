// Fit the phone pose so our avatar lands exactly where the reference avatar is (centre + ellipse), 2.10-4.30 s at 30 fps.
import { createRequire } from 'module'; import fs from 'fs'; import path from 'path';
const require = createRequire(import.meta.url);
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const track = JSON.parse(fs.readFileSync('build/fit/avatar_track.json'));
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 720, height: 1280 }, deviceScaleFactor: .25 });
await page.goto('file://' + path.resolve('index.html')); await page.evaluate(() => window.ready);
await page.evaluate(() => { const av = document.querySelector('#avatar');
  for (const [id, l, t] of [['mL', 0, 85], ['mR', 170, 85], ['mT', 85, 0], ['mB', 85, 170], ['mC', 85, 85]]) { const m = document.createElement('i');
    m.id = id; m.style.cssText = `position:absolute;left:${l}px;top:${t}px;width:1px;height:1px;display:block`; av.appendChild(m); } });
const meas = (q, ry) => page.evaluate(([q, ry]) => { window.posePhone(130, 279, q[0], q[1], q[2], q[3], ry, q[4]);
  const c = id => { const r = document.getElementById(id).getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; };
  return { L: c('mL'), R: c('mR'), T: c('mT'), B: c('mB'), C: c('mC') }; }, [q, ry]);
const err = (m, r) => { const a = [(m.R[0] - m.L[0]) / 2, (m.R[1] - m.L[1]) / 2], b = [(m.B[0] - m.T[0]) / 2, (m.B[1] - m.T[1]) / 2];
  const C = [a[0] * a[0] + b[0] * b[0], a[0] * a[1] + b[0] * b[1], a[1] * a[1] + b[1] * b[1]];
  const dc = (m.C[0] - r.cx) ** 2 + (m.C[1] - r.cy) ** 2;
  const dC = (C[0] - r.cxx) ** 2 + 2 * (C[1] - r.cxy) ** 2 + (C[2] - r.cyy) ** 2;
  return dc + Math.sqrt(dC) * 1.5; };
const out = []; let q = null;
for (const r of track) {
  if (!r || r.t < 2.1 || r.t > 4.3) continue;
  // the hologram rings join the blob after 3.35 s: trust only the centre there, keep size from the trend
  const ry = r.t < 2.95 ? 360 : r.t < 3.3 ? 360 + 22 * Math.sin(Math.PI * (r.t - 2.95) / .35) : 360;
  await page.evaluate(t => window.seek(t), r.t);
  if (!q) { const k = await page.evaluate(t => window.phoneAt(t), r.t); q = [k[3] + (130 - k[1]) * k[5], k[4] + (279 - k[2]) * k[5] * .7, k[5], k[6], k[8]]; }
  const rr = r.t > 3.35 ? { ...r, cxx: out.length ? undefined : r.cxx } : r;
  const f = async (x) => { const m = await meas(x, ry); if (r.t > 3.35) { return (m.C[0] - r.cx) ** 2 + (m.C[1] - r.cy) ** 2 + 4000 * (x[2] - q0[2]) ** 2 + 2 * (x[3] - q0[3]) ** 2 + 2 * (x[4] - q0[4]) ** 2; } return err(m, r); };
  var q0 = q.slice();
  let best = q.slice(), bs = await f(best), step = [30, 30, best[2] * .08, 5, 5];
  for (let it = 0; it < 14; it++) { let imp = false;
    for (let d = 0; d < 5; d++) for (const s of [1, -1]) { const x = best.slice(); x[d] += s * step[d]; if (x[2] < .2) continue; const v = await f(x); if (v < bs) { bs = v; best = x; imp = true; } }
    if (!imp) step = step.map(v => v / 2); }
  q = best; out.push([r.t, 130, 279, ...best.slice(0, 2), best[2], best[3], ry, best[4]].map(v => +(+v).toFixed(3)));
  console.log(r.t.toFixed(3), bs.toFixed(1), best.map(v => v.toFixed(2)).join(' '));
}
fs.writeFileSync('build/fit/avatar_fit.json', JSON.stringify(out)); await browser.close();
