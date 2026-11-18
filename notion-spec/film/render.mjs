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
  const sub = +(args.sub || 2), vf = sub > 1 ? `tmix=frames=${sub},select='eq(mod(n\\,${sub})\\,${sub - 1})',setpts=N/(${fps}*TB)` : 'null';
  const ff = spawn('ffmpeg', ['-y', '-v', 'error', '-f', 'image2pipe', '-framerate', String(fps * sub), '-i', '-', '-vf', vf, '-r', String(fps), '-c:v', 'libx264', '-preset', 'medium', '-crf', '16', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', outv], { stdio: ['pipe', 'inherit', 'inherit'] });
  const t0 = Date.now();
  // motion blur: `sub` samples spread over a 180-degree shutter, averaged by tmix
  for (let i = 0; i < N; i++) { for (let k = 0; k < sub; k++) { const b = await shot(Math.max(0, i / fps + ((k + .5) / sub - .5) * .5 / fps)); if (!ff.stdin.write(b)) await new Promise(r => ff.stdin.once('drain', r)); } if (i % 120 === 0) console.log(`frame ${i}/${N} ${((Date.now() - t0) / 1000).toFixed(0)}s`); }
  ff.stdin.end(); await new Promise(r => ff.on('close', r));
}
await browser.close(); srv.close();
