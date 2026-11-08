// node render.mjs [--times=0.5,1.2] [--out=dir] | full render -> frames piped to ffmpeg
import { createRequire } from 'module'; import http from 'http'; import fs from 'fs'; import path from 'path'; import { spawn } from 'child_process';
const require = createRequire(import.meta.url);
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const ROOT = path.dirname(new URL(import.meta.url).pathname);
const args = Object.fromEntries(process.argv.slice(2).map(a => { const [k, v] = a.replace(/^--/, '').split('='); return [k, v ?? true]; }));
const types = { '.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript', '.png': 'image/png', '.otf': 'font/otf', '.woff2': 'font/woff2', '.ttf': 'font/ttf', '.svg': 'image/svg+xml', '.json': 'application/json', '.jpg': 'image/jpeg' };
const srv = http.createServer((q, r) => { const f = path.join(ROOT, decodeURIComponent(q.url.split('?')[0])); fs.readFile(f, (e, d) => { if (e) { r.writeHead(404); r.end(); return; } r.writeHead(200, { 'Content-Type': types[path.extname(f)] || 'application/octet-stream' }); r.end(d); }); });
await new Promise(r => srv.listen(0, r)); const port = srv.address().port;
const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--force-color-profile=srgb'] });
const page = await browser.newPage({ viewport: { width: +(args.w || 1920), height: +(args.h || 1080) }, deviceScaleFactor: 1 });
page.on('console', m => { if (m.type() === 'error') console.error('PAGE:', m.text()); });
page.on('pageerror', e => { console.error('PAGEERR:', e.message); process.exit(3); });
await page.goto(`http://127.0.0.1:${port}/index.html`);
await page.waitForFunction(() => window.READY || window.INITERR, null, { timeout: 120000 });
const err = await page.evaluate(() => window.INITERR); if (err) { console.error(err); process.exit(1); }
const C = await page.evaluate(() => window.CUES); const fps = +(args.fps || C.fps);
const shot = async (t, tf) => { await page.evaluate(([t, tf]) => window.seek(t, tf), [t, tf ?? t]); return page.screenshot({ type: 'png', clip: { x: 0, y: 0, width: +(args.w || 1920), height: +(args.h || 1080) } }); };
if (args.times) {
  const out = args.out || path.join(ROOT, 'stills'); fs.mkdirSync(out, { recursive: true });
  for (const ts of String(args.times).split(',')) { const t = parseFloat(ts); fs.writeFileSync(path.join(out, `t${t.toFixed(2).padStart(6, '0')}.png`), await shot(t)); }
} else {
  const N = Math.round(C.dur * fps); const from = +(args.from || 0), to = +(args.to || N);
  const outv = args.video || path.join(ROOT, 'video.mp4');
  // motion blur: every output frame is the average of M equal-weight slots; a frame gets n ∈ {1,3,6} real sub-samples
  // spread over a 180° shutter (each repeated M/n times), so still frames cost one capture and fast ones get real blur
  const M = 6, plan = args.mb ? JSON.parse(fs.readFileSync(args.mb)) : null, shutter = +(args.shutter || 0.5);
  const vf = plan ? `tmix=frames=${M}:weights='${Array(M).fill(1).join(' ')}',select='eq(mod(n\\,${M})\\,${M - 1})',setpts=N/(${fps}*TB)` : 'null';
  const ff = spawn('ffmpeg', ['-y', '-v', 'error', '-f', 'image2pipe', '-framerate', String(plan ? fps * M : fps), '-i', '-', '-vf', vf, '-r', String(fps), '-c:v', 'libx264', '-preset', 'medium', '-crf', '16', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', outv], { stdio: ['pipe', 'inherit', 'inherit'] });
  const put = async (buf) => { if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r)); };
  const t0 = Date.now(); let caps = 0;
  for (let i = from; i < to; i++) {
    const tf = i / fps;
    if (!plan) { await put(await shot(tf)); caps++; }
    else { const n = plan[i] || 1;
      for (let k = 0; k < n; k++) { const buf = await shot(tf + ((k + .5) / n - .5) * shutter / fps, tf); caps++; for (let r = 0; r < M / n; r++) await put(buf); } }
    if (i % 60 === 0) console.log(`frame ${i}/${to} captures ${caps} ${((Date.now() - t0) / 1000).toFixed(0)}s`); }
  ff.stdin.end(); await new Promise(r => ff.on('close', r));
}
await browser.close(); srv.close();
