import { createRequire } from 'module'; import fs from 'fs'; import path from 'path';
const { chromium } = createRequire(import.meta.url)('/opt/node22/lib/node_modules/playwright');
const [key, fixf, timesf] = process.argv.slice(2);
const fix = JSON.parse(fs.readFileSync(fixf, 'utf8')); const times = JSON.parse(fs.readFileSync(timesf));
const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 720, height: 1280 }, deviceScaleFactor: .5 });
await p.addInitScript(([k, f]) => { window[k === 'G3B' ? 'G3FIX' : k] = f; }, [key, fix]);
await p.goto('file://' + path.resolve('index.html')); await p.evaluate(() => window.ready);
for (const t of times) { await p.evaluate(t => window.seek(t), t); await p.screenshot({ path: `build/lfit/o_${t.toFixed(3)}.png` }); }
await b.close();
