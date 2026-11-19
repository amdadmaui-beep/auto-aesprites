// node render.mjs --times=0.5,1.2 [--out=dir]   -> stills
// node render.mjs --video=build/video.mp4        -> full render, frames piped to ffmpeg
import { createRequire } from 'module'; import http from 'http'; import fs from 'fs'; import path from 'path'; import { spawn } from 'child_process';
const require = createRequire(import.meta.url);
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const ROOT = path.dirname(new URL(import.meta.url).pathname);
const args = Object.fromEntries(process.argv.slice(2).map(a => { const [k, v] = a.replace(/^--/, '').split('='); return [k, v ?? true]; }));
const types = { '.html': 'text/html', '.js': 'text/javascript', '.otf': 'font/otf', '.woff2': 'font/woff2', '.png': 'image/png', '.jpg': 'image/jpeg', '.svg': 'image/svg+xml' };
const srv = http.createServer((q, r) => { const f = path.join(ROOT, decodeURIComponent(q.url.split('?')[0])); fs.readFile(f, (e, d) => { if (e) { r.writeHead(404); r.end(); return; } r.writeHead(200, { 'Content-Type': types[path.extname(f)] || 'application/octet-stream' }); r.end(d); }); });
await new Promise(r => srv.listen(0, r)); const port = srv.address().port;
const browser = await chromium.launch({ args: ['--force-color-profile=srgb'] });
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
page.on('pageerror', e => { console.error('PAGEERR:', e.message); process.exit(3); });
await page.goto(`http://127.0.0.1:${port}/index.html${args.q ? '?' + args.q : ''}`);
await page.waitForFunction(() => window.READY || window.INITERR, null, { timeout: 120000 });
const err = await page.evaluate(() => window.INITERR); if (err) { console.error(err); process.exit(1); }
const C = await page.evaluate(() => window.CUES); const fps = +(args.fps || C.fps);
const shot = async t => { await page.evaluate(t => window.seek(t), t); return page.screenshot({ type: 'jpeg', quality: 95 }); };
if (args.times) {
  const out = args.out || path.join(ROOT, 'stills'); fs.mkdirSync(out, { recursive: true });
  for (const ts of String(args.times).split(',')) { const t = parseFloat(ts); fs.writeFileSync(path.join(out, `t${t.toFixed(2).padStart(5, '0')}.jpg`), await shot(t)); }
} else {
  const N = Math.round(C.dur * fps), outv = args.video || path.join(ROOT, 'build', 'video.mp4'); fs.mkdirSync(path.dirname(outv), { recursive: true });
  // motion blur: every output frame averages M=6 equal slots. Slow frames take 2 real samples (each repeated 3x),
  // frames inside the fast camera moves take 6, spread over a 180-degree shutter, so fast moves smear instead of doubling.
  const M = 6, HI = [[2.25, 2.95], [8.5, 9.1], [10.15, 11.05], [14.65, 15.15], [16.4, 16.9], [18.3, 22.7], [24.4, 25.9]];
  const nAt = t => HI.some(([a, b]) => t >= a && t <= b) ? 6 : 2;
  const vf = `tmix=frames=${M},select='eq(mod(n\\,${M})\\,${M - 1})',setpts=N/(${fps}*TB)`;
  const ff = spawn('ffmpeg', ['-y', '-v', 'error', '-f', 'image2pipe', '-framerate', String(fps * M), '-i', '-', '-vf', vf, '-r', String(fps), '-c:v', 'libx264', '-preset', 'medium', '-crf', '16', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', outv], { stdio: ['pipe', 'inherit', 'inherit'] });
  const t0 = Date.now(); let caps = 0;
  for (let i = 0; i < N; i++) { const n = nAt(i / fps);
    for (let k = 0; k < n; k++) { const b = await shot(Math.max(0, i / fps + ((k + .5) / n - .5) * .5 / fps)); caps++;
      for (let r = 0; r < M / n; r++) if (!ff.stdin.write(b)) await new Promise(res => ff.stdin.once('drain', res)); }
    if (i % 120 === 0) console.log(`frame ${i}/${N} captures ${caps} ${((Date.now() - t0) / 1000).toFixed(0)}s`); }
  ff.stdin.end(); await new Promise(r => ff.on('close', r));
}
await browser.close(); srv.close();
