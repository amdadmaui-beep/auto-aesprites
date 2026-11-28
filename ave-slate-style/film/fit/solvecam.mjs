// solve g3 camera correction (dx,dy,s) at key times so measured word centres/widths match the reference
import { createRequire } from 'module'; import fs from 'fs'; import path from 'path';
const { chromium } = createRequire(import.meta.url)('/opt/node22/lib/node_modules/playwright');
const KEYS = JSON.parse(fs.readFileSync(process.argv[2]));
const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 720, height: 1280 } });
await p.goto('file://' + path.resolve('index.html')); await p.evaluate(() => window.ready);
const out = [];
for (const [t, targets] of KEYS) {
  const err = async q => p.evaluate(([t, q, targets]) => { window.FIXO = q; window.seek(t); let e = 0;
    for (const [id, x, y, w] of targets) { const r = document.getElementById(id).getBoundingClientRect(); const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
      if (x != null) e += (cx - x) ** 2; if (y != null) e += (cy - y) ** 2; if (w) e += ((r.width - w) * 1.5) ** 2; }
    return e; }, [t, q, targets]);
  let best = out.length ? out[out.length - 1].slice(1) : [0, 0, 1], bs = await err(best), step = [80, 80, .15];
  for (let it = 0; it < 40; it++) { let imp = false;
    for (let d = 0; d < 3; d++) for (const sg of [1, -1]) { const x = best.slice(); x[d] += sg * step[d]; const v = await err(x); if (v < bs) { bs = v; best = x; imp = true; } }
    if (!imp) { step = step.map(v => v / 2); if (step[0] < .5) break; } }
  out.push([t, ...best.map(v => +v.toFixed(3))]); console.log(t, Math.sqrt(bs).toFixed(1), best.map(v => v.toFixed(2)).join(' '));
}
await p.evaluate(() => { window.FIXO = null; });
fs.writeFileSync(process.argv[3], JSON.stringify(out)); await b.close();
