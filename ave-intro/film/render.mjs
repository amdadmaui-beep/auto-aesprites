// Render the film: node render.mjs --times=1,2.5 (stills) | --video=build/video.mp4 [--sub=2]
import { createRequire } from 'module';
const { chromium } = createRequire(import.meta.url)('/opt/node22/lib/node_modules/playwright');
import { spawn } from 'child_process';
import fs from 'fs';
import path from 'path';
const arg = k => (process.argv.find(a => a.startsWith(`--${k}=`)) || '').split('=')[1];
const FPS = 30, SUB = +(arg('sub') || 2);
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1.5 });
await page.goto('file://' + path.resolve('index.html'));
await page.evaluate(() => window.ready);
const shot = async t => { await page.evaluate(t => window.seek(t), t); return page.screenshot({ type: 'jpeg', quality: 92 }); };
if (arg('times')) {
  fs.mkdirSync('build/stills', { recursive: true });
  for (const t of arg('times').split(',')) fs.writeFileSync(`build/stills/t${(+t).toFixed(2)}.jpg`, await shot(+t));
} else {
  const out = arg('video') || 'build/video.mp4';
  fs.mkdirSync(path.dirname(out), { recursive: true });
  const dur = await page.evaluate(() => window.DUR), N = Math.round(dur * FPS);
  // each output frame = average of SUB samples spread over a 180-degree shutter
  const ff = spawn('ffmpeg', ['-y', '-v', 'error', '-f', 'image2pipe', '-framerate', String(FPS * SUB), '-i', '-',
    '-vf', `tmix=frames=${SUB}:weights=${Array(SUB).fill(1).join(' ')},select='eq(mod(n\\,${SUB})\\,${SUB - 1})',setpts=N/${FPS}/TB`,
    '-r', String(FPS), '-c:v', 'libx264', '-crf', '15', '-preset', 'medium', '-pix_fmt', 'yuv420p', out], { stdio: ['pipe', 'inherit', 'inherit'] });
  for (let f = 0; f < N; f++) {
    for (let s = SUB - 1; s >= 0; s--) {
      const t = (f - s * 0.5 / SUB) / FPS;
      const buf = await shot(Math.max(0, t));
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    }
    if (f % 60 === 0) console.log(`frame ${f}/${N}`);
  }
  ff.stdin.end(); await new Promise(r => ff.on('close', r));
}
await browser.close();
