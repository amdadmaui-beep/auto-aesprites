// side-by-side ref | ours for given times and lens values -> build/cmp3_<lens>.jpg
import { createRequire } from 'module'; import fs from 'fs'; import path from 'path'; import { execSync } from 'child_process';
const { chromium } = createRequire(import.meta.url)('/opt/node22/lib/node_modules/playwright');
const times = process.argv[2].split(',').map(Number), lenses = (process.argv[3] || '800').split(',').map(Number), tag = process.argv[4] || 'c';
const b = await chromium.launch();
for (const L of lenses) {
  const p = await b.newPage({ viewport: { width: 720, height: 1280 }, deviceScaleFactor: .5 });
  await p.addInitScript(L => { window.LENS = L; }, L);
  await p.goto('file://' + path.resolve('index.html')); await p.evaluate(() => window.ready);
  const d = `build/${tag}_${L}`; fs.rmSync(d, { recursive: true, force: true }); fs.mkdirSync(d, { recursive: true });
  for (const t of times) { await p.evaluate(t => window.seek(t), t); await p.screenshot({ path: `${d}/o_${t.toFixed(3)}.png` });
    execSync(`ffmpeg -v error -y -ss ${t} -i ../../.reanimate/ref6/ref.mp4 -frames:v 1 -vf scale=360:640 ${d}/r_${t.toFixed(3)}.png`);
    execSync(`ffmpeg -v error -y -i ${d}/r_${t.toFixed(3)}.png -i ${d}/o_${t.toFixed(3)}.png -filter_complex "[0][1]hstack,drawtext=text='${t.toFixed(2)}':fontcolor=yellow:fontsize=26:x=8:y=8" ${d}/s_${t.toFixed(3)}.png`); }
  const cols = Math.min(6, times.length), rows = Math.ceil(times.length / cols);
  execSync(`ffmpeg -v error -y -pattern_type glob -i '${d}/s_*.png' -vf "scale=360:320,tile=${cols}x${rows}" build/${tag}_${L}.jpg`);
  await p.close(); }
await b.close();
