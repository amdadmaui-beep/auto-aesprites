import { createRequire } from 'module'; import fs from 'fs'; import path from 'path';
const require = createRequire(import.meta.url);
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const fit = JSON.parse(fs.readFileSync('build/fit/avatar_fit.json'));
const persp = +process.argv[2] || 1500;
const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 720, height: 1280 }, deviceScaleFactor: .5 });
await p.goto('file://' + path.resolve('index.html')); await p.evaluate(() => window.ready);
fs.rmSync('build/cmp2', { recursive: true, force: true }); fs.mkdirSync('build/cmp2', { recursive: true });
for (const r of fit.filter(r => r[0] >= 2.3 && r[0] <= 3.34 && Math.round(r[0] * 30) % 3 === 0)) { const [t, px, py, sx, sy, sc, rx, ry, rz] = r;
  await p.evaluate(([t, q]) => { window.seek(t); window.posePhone(...q); }, [t, [px, py, sx, sy, sc, rx, ry, rz, persp]]);
  fs.writeFileSync(`build/cmp2/o_${t.toFixed(3)}.png`, await p.screenshot()); }
await b.close();
