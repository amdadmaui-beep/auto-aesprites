// Renders film.html frame by frame: seek(t) -> screenshot -> PNG.
//   node render.mjs                     all frames into build/frames
//   node render.mjs --frames=0,30,60    only these frame indices
//   node render.mjs --beats             one frame per beat (from beats.json) into build/beats
import { chromium } from 'playwright';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.dirname(fileURLToPath(import.meta.url));
const args = Object.fromEntries(process.argv.slice(2).map(a => { const [k, v] = a.replace(/^--/, '').split('='); return [k, v ?? true]; }));
const FPS = +(args.fps || 60), DUR = 25, WORKERS = +(args.workers || 4);

let frames, outDir;
if (args.beats) {
  const beats = JSON.parse(fs.readFileSync(path.join(ROOT, 'beats.json'), 'utf8')).beats;
  frames = beats.map(b => Math.round(b * FPS)).filter(f => f < DUR * FPS);
  outDir = path.join(ROOT, 'build', 'beats');
} else if (args.frames) {
  frames = String(args.frames).split(',').map(Number);
  outDir = path.join(ROOT, 'build', 'stills');
} else {
  frames = Array.from({ length: DUR * FPS }, (_, i) => i);
  outDir = path.join(ROOT, 'build', 'frames');
}
fs.mkdirSync(outDir, { recursive: true });

const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.woff2': 'font/woff2', '.json': 'application/json' };
const server = http.createServer((req, res) => {
  const p = path.join(ROOT, decodeURIComponent(new URL(req.url, 'http://x').pathname));
  if (!p.startsWith(ROOT) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'content-type': MIME[path.extname(p)] || 'application/octet-stream' });
  fs.createReadStream(p).pipe(res);
}).listen(0);
const url = `http://127.0.0.1:${server.address().port}/film.html`;

const browser = await chromium.launch({ args: ['--disable-gpu-vsync', '--force-color-profile=srgb'] });
let next = 0, done = 0;
const t0 = Date.now();
async function worker() {
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  page.on('pageerror', e => { console.error('PAGE ERROR', e.message); process.exitCode = 1; });
  await page.goto(url);
  await page.evaluate(() => window.ready);
  while (next < frames.length) {
    const f = frames[next++];
    await page.evaluate(t => window.seek(t), f / FPS);
    await page.screenshot({ path: path.join(outDir, `f_${String(f).padStart(5, '0')}.png`), type: 'png' });
    if (++done % 100 === 0) console.log(`${done}/${frames.length}  ${((Date.now() - t0) / 1000).toFixed(1)}s`);
  }
  await page.close();
}
await Promise.all(Array.from({ length: Math.min(WORKERS, frames.length) }, worker));
await browser.close();
server.close();
console.log(`rendered ${frames.length} frames to ${path.relative(ROOT, outDir)} in ${((Date.now() - t0) / 1000).toFixed(1)}s`);
