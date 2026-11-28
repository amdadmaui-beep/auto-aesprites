import { createRequire } from 'module'; import fs from 'fs'; import path from 'path';
const require = createRequire(import.meta.url);
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const fit = JSON.parse(fs.readFileSync('build/fit/full_fit.json'));
const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 720, height: 1280 }, deviceScaleFactor: .5 });
await p.goto('file://' + path.resolve('index.html')); await p.evaluate(() => window.ready);
fs.mkdirSync('build/cmpfit', { recursive: true });
for (const r of fit.filter((r, i) => i % 4 === 0)) { const [t, sx, sy, sc, rx, rz, persp, ry] = r;
  await p.evaluate(([t, q]) => { window.seek(t); window.posePhone(130, 279, q[0], q[1], q[2], q[3], q[6], q[4], q[5]); }, [t, [sx, sy, sc, rx, rz, persp, ry]]);
  fs.writeFileSync(`build/cmpfit/o_${t.toFixed(3)}.png`, await p.screenshot()); }
await b.close();
