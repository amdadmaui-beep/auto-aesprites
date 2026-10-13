// node render.mjs [--times=0.5,1.2] [--out=dir] | full render -> frames piped to ffmpeg
import { createRequire } from 'module'; import http from 'http'; import fs from 'fs'; import path from 'path'; import { spawn } from 'child_process';
const require = createRequire(import.meta.url);
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const ROOT = path.dirname(new URL(import.meta.url).pathname);
const args = Object.fromEntries(process.argv.slice(2).map(a => { const [k, v] = a.replace(/^--/, '').split('='); return [k, v ?? true]; }));
const types = { '.html': 'text/html', '.js': 'text/javascript', '.png': 'image/png', '.otf': 'font/otf', '.woff2': 'font/woff2', '.json': 'application/json', '.jpg': 'image/jpeg' };
const srv = http.createServer((q, r) => { const f = path.join(ROOT, decodeURIComponent(q.url.split('?')[0])); fs.readFile(f, (e, d) => { if (e) { r.writeHead(404); r.end(); return; } r.writeHead(200, { 'Content-Type': types[path.extname(f)] || 'application/octet-stream' }); r.end(d); }); });
await new Promise(r => srv.listen(0, r)); const port = srv.address().port;
const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--force-color-profile=srgb'] });
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
page.on('console', m => { if (m.type() === 'error') console.error('PAGE:', m.text()); });
page.on('pageerror', e => { console.error('PAGEERR:', e.message); process.exit(3); });
await page.goto(`http://127.0.0.1:${port}/index.html`);
await page.waitForFunction(() => window.READY || window.INITERR, null, { timeout: 120000 });
const err = await page.evaluate(() => window.INITERR); if (err) { console.error(err); process.exit(1); }
const C = await page.evaluate(() => window.CUES); const fps = +(args.fps || C.fps);
const shot = async (t) => { await page.evaluate(t => window.seek(t), t); return page.screenshot({ type: 'png', clip: { x: 0, y: 0, width: 1920, height: 1080 } }); };
if (args.times) {
  const out = args.out || path.join(ROOT, 'stills'); fs.mkdirSync(out, { recursive: true });
  for (const ts of String(args.times).split(',')) { const t = parseFloat(ts); fs.writeFileSync(path.join(out, `t${t.toFixed(2).padStart(6, '0')}.png`), await shot(t)); }
} else {
  const N = Math.round(C.dur * fps); const from = +(args.from || 0), to = +(args.to || N);
  const outv = args.video || path.join(ROOT, 'video.mp4');
  const ff = spawn('ffmpeg', ['-y', '-v', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', '16', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', outv], { stdio: ['pipe', 'inherit', 'inherit'] });
  const t0 = Date.now();
  for (let i = from; i < to; i++) { const buf = await shot(i / fps); if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r)); if (i % 60 === 0) console.log(`frame ${i}/${to} ${((Date.now() - t0) / 1000).toFixed(0)}s`); }
  ff.stdin.end(); await new Promise(r => ff.on('close', r));
}
await browser.close(); srv.close();
