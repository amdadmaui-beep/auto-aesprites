'use strict';
// Motion reel — every frame is a pure function of time: window.seek(t) paints frame t.
// No timers, no transitions, no state carried between frames. Seeded noise only.

const W = 1920, H = 1080, DUR = 25;
const INK = '#0D0D0F', PAPER = '#EEEAE2', ACC = '#FF4B1F', GRAY = '#8C8880', RULE = '#3A3A40', SOFT = '#1C1C20';
const DISP = 'Archivo', MONO = '"JetBrains Mono"';
// studio name on the reel — change here, or preview with film.html?name=YOURSTUDIO
const STUDIO = (new URLSearchParams(location.search).get('name') || 'GEMINI').toUpperCase();
const TAU = Math.PI * 2;

// ---------------------------------------------------------------- math
const clamp = (x, a = 0, b = 1) => (x < a ? a : x > b ? b : x);
const lerp = (a, b, t) => a + (b - a) * t;
const prog = (t, a, b) => clamp((t - a) / (b - a));
const E = {
  inCubic: x => x * x * x,
  outCubic: x => 1 - Math.pow(1 - x, 3),
  inOutCubic: x => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2),
  outQuart: x => 1 - Math.pow(1 - x, 4),
  inExpo: x => (x <= 0 ? 0 : Math.pow(2, 10 * x - 10)),
  outExpo: x => (x >= 1 ? 1 : 1 - Math.pow(2, -10 * x)),
  inOutExpo: x => (x <= 0 ? 0 : x >= 1 ? 1 : x < 0.5 ? Math.pow(2, 20 * x - 10) / 2 : (2 - Math.pow(2, -20 * x + 10)) / 2),
  outBack: (x, s = 1.70158) => 1 + (s + 1) * Math.pow(x - 1, 3) + s * Math.pow(x - 1, 2),
};
// damped spring step response, 0 -> 1
function spring(t, f = 3, z = 0.4) {
  if (t <= 0) return 0;
  const w = TAU * f, wd = w * Math.sqrt(1 - z * z);
  return 1 - Math.exp(-z * w * t) * (Math.cos(wd * t) + (z * w / wd) * Math.sin(wd * t));
}
// a single hump 0 -> 1 -> 0 over [0, len]
const bump = (x, len) => (x <= 0 || x >= len ? 0 : Math.sin(Math.PI * x / len));

function mulberry32(a) {
  return function () {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
// seeds derive from element ids, never from call order
const rnd = (id, k = 0) => mulberry32((Math.imul(id + 1, 0x9e3779b1) ^ Math.imul(k + 7, 0x85ebca77)) >>> 0)();

function cubicBezier(x1, y1, x2, y2) {
  const cx = 3 * x1, bx = 3 * (x2 - x1) - cx, ax = 1 - cx - bx;
  const cy = 3 * y1, by = 3 * (y2 - y1) - cy, ay = 1 - cy - by;
  const sx = s => ((ax * s + bx) * s + cx) * s, sy = s => ((ay * s + by) * s + cy) * s;
  return x => {
    if (x <= 0) return 0; if (x >= 1) return 1;
    let lo = 0, hi = 1, s = x;
    for (let i = 0; i < 40; i++) { if (sx(s) < x) lo = s; else hi = s; s = (lo + hi) / 2; }
    return sy(s);
  };
}

// ---------------------------------------------------------------- text
function setFont(ctx, px, wght = 900, fam = DISP, stretch = 'normal') {
  ctx.font = `${Math.round(wght)} ${px}px ${fam}`;
  ctx.fontStretch = stretch;
}
const mcache = new Map(); // pure memo of glyph widths, not animation state
function tw(ctx, s) {
  const k = ctx.font + '|' + ctx.fontStretch + '|' + s;
  let v = mcache.get(k);
  if (v === undefined) { v = ctx.measureText(s).width; mcache.set(k, v); }
  return v;
}
// characters visible for a type-on that may later be deleted
function typedCount(str, t, t0, cps, del0 = Infinity, delCps = 160) {
  let n = clamp(Math.floor((t - t0) * cps), 0, str.length);
  if (t > del0) n = Math.min(n, Math.max(0, str.length - Math.floor((t - del0) * delCps)));
  return n;
}
// section label: accent index + typed caption + accent caret
function label(ctx, num, text, x, y, t, t0, color = PAPER, size = 32, align = 'left', numColor = ACC) {
  const full = num + '   ' + text;
  const cps = 48;
  const n = typedCount(full, t, t0, cps);
  if (t < t0) return;
  setFont(ctx, size, 700, MONO);
  ctx.textBaseline = 'alphabetic';
  const fullW = tw(ctx, full);
  const x0 = align === 'center' ? x - fullW / 2 : x;
  const s = full.slice(0, n);
  const a = s.slice(0, num.length), b = s.slice(num.length);
  ctx.fillStyle = numColor; ctx.fillText(a, x0, y);
  ctx.fillStyle = color; setFont(ctx, size, 400, MONO); ctx.fillText(b, x0 + tw(ctx, a), y);
  const done = t0 + full.length / cps;
  if (t < done + 0.3) {
    setFont(ctx, size, 400, MONO);
    ctx.fillStyle = numColor;
    ctx.fillRect(x0 + tw(ctx, s) + 4, y - size * 0.8, size * 0.55, size);
  }
}
function typeLine(ctx, str, x, y, t, t0, { size = 22, wght = 400, color = PAPER, cps = 48, del0 = Infinity, caret = true } = {}) {
  if (t < t0) return;
  const n = typedCount(str, t, t0, cps, del0);
  setFont(ctx, size, wght, MONO);
  ctx.fillStyle = color; ctx.textBaseline = 'alphabetic';
  const s = str.slice(0, n);
  ctx.fillText(s, x, y);
  const done = t0 + str.length / cps;
  if (caret && n > 0 && (t < done + 0.3 || t > del0) ) {
    ctx.fillStyle = ACC;
    ctx.fillRect(x + tw(ctx, s) + 4, y - size * 0.8, size * 0.55, size);
  }
}

// draws a glyph whose scale is anchored at its baseline centre and rotation at its body centre
function glyph(ctx, ch, x, bl, w, capH, o = {}) {
  ctx.save();
  ctx.translate(x + w / 2 + (o.dx || 0), bl - capH / 2 + (o.dy || 0));
  if (o.rot) ctx.rotate(o.rot);
  ctx.translate(0, capH / 2);
  ctx.scale(o.sx || 1, o.sy || 1);
  if (o.stroke) { ctx.strokeText(ch, -w / 2, 0); } else ctx.fillText(ch, -w / 2, 0);
  ctx.restore();
}

function ellipseBall(ctx, x, y, rx, ry, rot, color) {
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.ellipse(x, y, Math.max(0.01, rx), Math.max(0.01, ry), rot, 0, TAU);
  ctx.fill();
}

// ======================================================================
// SCENE A — 0.0–4.0  hook type "WE MAKE THINGS MOVE." then the period bounces
// ======================================================================
const A_X0 = 150, A_FS = 236, A_BL = [292, 512, 732, 952], FLOOR = 952, A_CAP = A_FS * 0.72;
const A_LINES = ['WE', 'MAKE', 'THINGS', 'MOVE'];

function fallX(t, id) {
  const d = 0.025 * Math.floor(id / 10) + rnd(id, 1) * 0.14;
  const tl = t - 2.0 - d;
  if (tl <= 0) return null;
  return { dx: (rnd(id, 2) - 0.5) * 560 * tl, dy: -(240 + rnd(id, 4) * 340) * tl + 0.5 * 7400 * tl * tl, rot: (rnd(id, 3) - 0.5) * 7 * tl };
}

function periodPos(ctx) {
  setFont(ctx, A_FS, 900);
  return { x: A_X0 + tw(ctx, 'MOVE') + 18 + 26, y: FLOOR };
}

const HOPS = [
  { t0: 2.0, t1: 2.5, x1: 1130, h: 500, imp: 1.0 },
  { t0: 2.5, t1: 3.0, x1: 1330, h: 350, imp: 0.9 },
  { t0: 3.0, t1: 3.5, x1: 1490, h: 225, imp: 0.75 },
  { t0: 3.5, t1: 4.0, x1: 1610, h: 125, imp: 0.6 },
];
const ballR = t => lerp(26, 46, E.outCubic(prog(t, 2.0, 2.4)));

// returns bottom-centre position of the undeformed ball
function ballPath(ctx, t) {
  const p0 = periodPos(ctx);
  if (t <= 2.0) return { x: p0.x, yb: FLOOR, vx: 0, vy: 0 };
  let x0 = p0.x;
  for (let k = 0; k < HOPS.length; k++) {
    const hp = HOPS[k], c = k === 0 ? 0 : 0.035;
    if (t < hp.t1 || k === HOPS.length - 1) {
      const T = hp.t1 - hp.t0 - c;
      const u = prog(t, hp.t0 + c, hp.t1);
      return { x: lerp(x0, hp.x1, u), yb: FLOOR - hp.h * 4 * u * (1 - u), vx: (hp.x1 - x0) / T, vy: -hp.h * 4 * (1 - 2 * u) / T, u };
    }
    x0 = hp.x1;
  }
}

function drawBall(ctx, t) {
  if (t < 1.75) return;
  const p = ballPath(ctx, t);
  const r = ballR(t) * (t < 2.0 ? E.outBack(prog(t, 1.75, 1.93), 2.2) : 1);
  // squash: anticipation before launch and on each landing
  let sq = 0;
  if (t < 2.02) sq = 0.32 * E.inOutCubic(prog(t, 1.88, 2.0)) * (1 - prog(t, 2.0, 2.02));
  for (let k = 0; k < HOPS.length; k++) {
    const d = t - HOPS[k].t1;
    if (d >= 0 && d < 0.09) sq = Math.max(sq, HOPS[k].imp * 0.5 * Math.sin(Math.PI * d / 0.09));
  }
  if (sq > 0.01) {
    const sy = 1 - sq, sx = 1 + sq * 0.8;
    ellipseBall(ctx, p.x, p.yb - r * sy, r * sx, r * sy, 0, ACC);
  } else {
    const v = Math.hypot(p.vx, p.vy);
    const s = clamp(v / 5200, 0, 0.42);
    ellipseBall(ctx, p.x, p.yb - r * (1 + s * Math.abs(p.vy) / Math.max(v, 1e-6)), r * (1 + s), r * (1 - s * 0.55), Math.atan2(p.vy, p.vx), ACC);
  }
}

function sceneA(ctx, t) {
  ctx.fillStyle = INK; ctx.fillRect(0, 0, W, H);
  ctx.textBaseline = 'alphabetic';

  // ---- bounce rig (behind the type) ----
  if (t > 2.0) {
    const pp = periodPos(ctx);
    const e = E.outExpo(prog(t, 2.0, 2.5));
    ctx.strokeStyle = RULE; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(lerp(pp.x, A_X0, e), FLOOR + 1); ctx.lineTo(lerp(pp.x, 1770, e), FLOOR + 1); ctx.stroke();
    // dotted motion path
    ctx.save();
    ctx.setLineDash([2, 12]); ctx.lineCap = 'round'; ctx.strokeStyle = GRAY; ctx.lineWidth = 3;
    ctx.beginPath();
    for (let τ = 2.0; τ <= t; τ += 1 / 120) {
      const q = ballPath(ctx, τ), r = ballR(τ);
      if (τ === 2.0) ctx.moveTo(q.x, q.yb - r); else ctx.lineTo(q.x, q.yb - r);
    }
    ctx.stroke(); ctx.restore();
    // onion skin every 5 frames (spacing chart)
    ctx.lineWidth = 2;
    for (let j = 0; j < 200; j++) {
      const τ = 2.0 + j / 12;
      if (τ > t) break;
      const age = t - τ;
      if (age > 0.85) continue;
      const q = ballPath(ctx, τ), r = ballR(τ);
      ctx.strokeStyle = `rgba(140,136,128,${0.7 * (1 - age / 0.85)})`;
      ctx.beginPath(); ctx.arc(q.x, q.yb - r, r, 0, TAU); ctx.stroke();
    }
    // landing ticks with frame numbers
    setFont(ctx, 17, 400, MONO);
    for (const hp of HOPS) {
      if (t < hp.t1) continue;
      const e2 = E.outExpo(prog(t, hp.t1, hp.t1 + 0.25));
      ctx.fillStyle = ACC; ctx.fillRect(hp.x1 - 1.5, FLOOR + 10, 3, 22 * e2);
      typeLine(ctx, 'F' + String(Math.round(hp.t1 * 60)).padStart(3, '0'), hp.x1 - 26, FLOOR + 66, t, hp.t1 + 0.04, { size: 24, color: GRAY, cps: 60, caret: false });
    }
    label(ctx, '01', 'TIMING  ·  SPACING  ·  SQUASH & STRETCH', A_X0, FLOOR - 44, t, 2.2, PAPER);
  }

  // ---- hook type ----
  setFont(ctx, A_FS, 900);
  const tF = t; // falls after 2.0
  // line 0 — "WE" slams down from a screen-filling slab on frame 0
  {
    const s0 = A_LINES[0], ww = tw(ctx, s0);
    const sp = spring(t, 2.1, 0.42);
    const sc = Math.pow(Math.max(1.5, 1500 / ww), 1 - sp);
    // word centre travels from screen centre to its slot while scaling down
    const hx = A_X0 + ww / 2, hy = A_BL[0] - A_CAP / 2;
    ctx.save();
    ctx.translate(lerp(W / 2, hx, sp), lerp(H / 2, hy, sp)); ctx.scale(sc, sc); ctx.translate(-hx, -hy);
    ctx.fillStyle = PAPER;
    for (let i = 0; i < s0.length; i++) glyph(ctx, s0[i], A_X0 + tw(ctx, s0.slice(0, i)), A_BL[0], tw(ctx, s0[i]), A_CAP, fallX(tF, i) || {});
    ctx.restore();
  }
  // intro mono next to "WE"
  {
    setFont(ctx, A_FS, 900);
    const x = A_X0 + tw(ctx, A_LINES[0]) + 46;
    typeLine(ctx, STUDIO, x, A_BL[0] - 104, t, 0.2, { size: 40, wght: 700, color: PAPER, cps: 30, del0: 1.86 });
    typeLine(ctx, 'MOTION STUDIO  /  REEL 2026', x, A_BL[0] - 52, t, 0.42, { size: 28, color: GRAY, cps: 70, del0: 1.86 });
  }
  // line 1 — MAKE rises out of its baseline
  if (t >= 0.44) {
    setFont(ctx, A_FS, 900); ctx.fillStyle = PAPER;
    const s = 'MAKE';
    ctx.save();
    if (t < 2.0) { ctx.beginPath(); ctx.rect(0, A_BL[1] - A_FS, W, A_FS + 4); ctx.clip(); }
    for (let i = 0; i < s.length; i++) {
      const p = E.outExpo(prog(t, 0.44 + i * 0.04, 0.44 + i * 0.04 + 0.45));
      const x = A_X0 + tw(ctx, s.slice(0, i));
      const f = fallX(tF, 10 + i) || {};
      glyph(ctx, s[i], x, A_BL[1], tw(ctx, s[i]), A_CAP, { ...f, dy: (f.dy || 0) + (1 - p) * A_FS * 0.98 });
    }
    ctx.restore();
  }
  // line 2 — THINGS: weight sweeps 100 -> 900 letter by letter
  if (t >= 0.94) {
    const s = 'THINGS';
    let x = A_X0;
    ctx.fillStyle = PAPER;
    for (let i = 0; i < s.length; i++) {
      const ts = 0.94 + i * 0.045;
      if (t < ts) break;
      const p = prog(t, ts, ts + 0.34);
      const wg = lerp(100, 900, E.outCubic(p));
      setFont(ctx, A_FS, wg);
      const w = tw(ctx, s[i]);
      const f = fallX(tF, 20 + i) || {};
      glyph(ctx, s[i], x, A_BL[2], w, A_CAP, { ...f, dy: (f.dy || 0) - 46 * Math.sin(Math.PI * p) });
      x += w;
    }
  }
  // line 3 — MOVE slams in from the right with shutter smear, in accent
  if (t >= 1.44) {
    setFont(ctx, A_FS, 900);
    const s = 'MOVE';
    const off = (tt, i) => (1 - E.outExpo(prog(tt, 1.44 + i * 0.035, 1.44 + i * 0.035 + 0.42))) * 1150;
    for (let i = 0; i < s.length; i++) {
      const x = A_X0 + tw(ctx, s.slice(0, i));
      const w = tw(ctx, s[i]);
      const f = fallX(tF, 30 + i) || {};
      const o = off(t, i), smear = off(t - 1 / 90, i) - o;
      for (let k = 4; k >= 1; k--) {
        if (smear < 4) break;
        ctx.globalAlpha = 0.22 * (1 - k / 5);
        ctx.fillStyle = ACC;
        glyph(ctx, s[i], x + o + smear * k / 4, A_BL[3], w, A_CAP, f);
      }
      ctx.globalAlpha = 1; ctx.fillStyle = ACC;
      glyph(ctx, s[i], x + o, A_BL[3], w, A_CAP, f);
    }
  }
  drawBall(ctx, t);
}

// ======================================================================
// SCENE B — 4.0–6.5  easing / graph editor
// ======================================================================
const CURVES = [
  { name: 'linear', h: [0, 0, 1, 1] },
  { name: 'ease out', h: [0.16, 1, 0.3, 1] },
  { name: 'ease in-out', h: [0.7, 0, 0.2, 1] },
  { name: 'overshoot', h: [0.34, 1.56, 0.64, 1] },
  { name: 'spring', h: null, f: x => spring(x, 2.6, 0.3) },
];
for (const c of CURVES) if (c.h) c.f = cubicBezier(...c.h);
const B_T0 = 4.0;
const G = { x: 220, y: 780, w: 640, h: 420 }; // value 0 at y, value 1 at y-h
const gx = u => G.x + u * G.w, gy = v => G.y - v * G.h;
const TX0 = 1060, TX1 = 1740, TY = 560, SQ = 84;

function sceneB(ctx, t) {
  ctx.fillStyle = ACC; ctx.fillRect(0, 0, W, H);
  const k = clamp(Math.floor((t - B_T0) / 0.5), 0, CURVES.length - 1);
  const Tk = B_T0 + k * 0.5;
  const cur = CURVES[k], prev = CURVES[Math.max(0, k - 1)];
  const m = k === 0 ? 1 : E.inOutCubic(prog(t, Tk, Tk + 0.16));
  const g = x => lerp(prev.f(x), cur.f(x), m);

  // axes + grid
  const ax = E.outExpo(prog(t, 4.05, 4.45));
  ctx.strokeStyle = 'rgba(13,13,15,0.16)'; ctx.lineWidth = 2;
  for (let i = 1; i <= 4; i++) {
    ctx.beginPath(); ctx.moveTo(G.x, gy(i / 4)); ctx.lineTo(G.x + G.w * ax, gy(i / 4)); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(gx(i / 4), G.y); ctx.lineTo(gx(i / 4), G.y - (G.h + 60) * ax); ctx.stroke();
  }
  ctx.strokeStyle = INK; ctx.lineWidth = 4;
  ctx.beginPath(); ctx.moveTo(G.x, G.y - (G.h + 140) * ax); ctx.lineTo(G.x, G.y); ctx.lineTo(G.x + (G.w + 40) * ax, G.y); ctx.stroke();
  setFont(ctx, 22, 700, MONO); ctx.fillStyle = INK;
  if (t > 4.2) { ctx.fillText('VALUE', G.x + 14, G.y - G.h - 120); ctx.fillText('TIME', G.x + G.w - 20, G.y + 36); }

  // the curve, drawn on with a trim
  const trim = E.inOutCubic(prog(t, 4.08, 4.42));
  ctx.strokeStyle = INK; ctx.lineWidth = 8; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
  ctx.beginPath();
  const N = 120;
  for (let i = 0; i <= N * trim; i++) {
    const u = i / N;
    if (i === 0) ctx.moveTo(gx(u), gy(g(u))); else ctx.lineTo(gx(u), gy(g(u)));
  }
  ctx.stroke();

  // bezier handles
  const hp = prev.h || [0, 0, 1, 1], hc = cur.h || [0, 0, 1, 1];
  const vis = (cur.h ? 1 : 1 - m) * (prev.h || k === 0 ? 1 : m) * E.outBack(prog(t, 4.3, 4.55));
  if (vis > 0.01) {
    const hx1 = lerp(hp[0], hc[0], m), hy1 = lerp(hp[1], hc[1], m), hx2 = lerp(hp[2], hc[2], m), hy2 = lerp(hp[3], hc[3], m);
    ctx.lineWidth = 2; ctx.strokeStyle = INK;
    const knob = (x, y) => { const s = 18 * vis; ctx.fillStyle = PAPER; ctx.fillRect(x - s / 2, y - s / 2, s, s); ctx.strokeRect(x - s / 2, y - s / 2, s, s); };
    ctx.beginPath(); ctx.moveTo(gx(0), gy(0)); ctx.lineTo(gx(hx1), gy(hy1)); ctx.moveTo(gx(1), gy(1)); ctx.lineTo(gx(hx2), gy(hy2)); ctx.stroke();
    knob(gx(hx1), gy(hy1)); knob(gx(hx2), gy(hy2));
  }
  // keys
  ctx.fillStyle = INK;
  for (const [u, v] of [[0, 0], [1, 1]]) {
    ctx.save(); ctx.translate(gx(u), gy(v)); ctx.rotate(Math.PI / 4); const s = 22 * trim; ctx.fillRect(-s / 2, -s / 2, s, s); ctx.restore();
  }

  // playhead on curve
  const u = prog(t, Tk + 0.04, Tk + 0.44);
  if (t > 4.2) {
    ctx.save(); ctx.setLineDash([4, 8]); ctx.lineWidth = 2; ctx.strokeStyle = INK;
    ctx.beginPath(); ctx.moveTo(gx(u), G.y); ctx.lineTo(gx(u), gy(g(u))); ctx.lineTo(G.x, gy(g(u))); ctx.stroke(); ctx.restore();
    ctx.fillStyle = INK; ctx.beginPath(); ctx.arc(gx(u), gy(g(u)), 13, 0, TAU); ctx.fill();
    ctx.fillStyle = PAPER; ctx.beginPath(); ctx.arc(gx(u), gy(g(u)), 5, 0, TAU); ctx.fill();
  }

  // track + object + spacing ghosts
  const tr = E.outExpo(prog(t, 4.15, 4.6));
  ctx.strokeStyle = 'rgba(13,13,15,0.3)'; ctx.lineWidth = 2;
  ctx.beginPath(); ctx.moveTo(TX0, TY + SQ / 2); ctx.lineTo(lerp(TX0, TX1, tr), TY + SQ / 2); ctx.stroke();
  const posOf = (v, kk) => (kk % 2 === 0 ? lerp(TX0, TX1 - SQ, v) : lerp(TX1 - SQ, TX0, v));
  ctx.lineWidth = 2;
  for (let j = 0; j <= 10; j++) {
    if (j / 10 > u + 1e-6) break;
    ctx.strokeStyle = 'rgba(13,13,15,0.35)';
    ctx.beginPath(); ctx.roundRect(posOf(cur.f(j / 10), k), TY - SQ / 2, SQ, SQ, 14); ctx.stroke();
  }
  if (t > 4.15) {
    const sc = E.outBack(prog(t, 4.15, 4.4), 2);
    const x = posOf(cur.f(u), k);
    ctx.fillStyle = INK; ctx.beginPath();
    ctx.roundRect(x + SQ / 2 - SQ * sc / 2, TY - SQ * sc / 2, SQ * sc, SQ * sc, 14 * sc); ctx.fill();
  }

  // big name, rolling up on change
  setFont(ctx, 112, 900); ctx.fillStyle = INK;
  ctx.save(); ctx.beginPath(); ctx.rect(TX0 - 10, 270, 900, 150); ctx.clip();
  const roll = k === 0 ? E.outExpo(prog(t, 4.2, 4.55)) : E.outExpo(prog(t, Tk, Tk + 0.3));
  if (k > 0) ctx.fillText(prev.name, TX0, 400 - roll * 150);
  ctx.fillText(cur.name, TX0, 400 + (1 - roll) * 150);
  ctx.restore();
  // parameter readout
  let txt;
  if (cur.h && (prev.h || k === 0)) {
    const v = hc.map((c, i) => lerp(hp[i], c, m).toFixed(2));
    txt = `cubic-bezier(${v.join(', ')})`;
  } else if (!cur.h) txt = 'spring(mass 1, stiffness 260, damping 10)';
  else txt = '';
  if (t > 4.3) { setFont(ctx, 28, 400, MONO); ctx.fillStyle = INK; ctx.fillText(txt, TX0, TY + SQ / 2 + 70); }

  label(ctx, '02', 'EASING  ·  GRAPH EDITOR  ·  SPACING', G.x, 985, t, 4.35, INK, 32, 'left', PAPER);
}

// ======================================================================
// SCENE C — 6.5–8.5  morph + stagger grid
// ======================================================================
function polyRadial(verts, N = 96) {
  const out = new Float32Array(N);
  for (let i = 0; i < N; i++) {
    const th = (i / N) * TAU, dx = Math.cos(th), dy = Math.sin(th);
    let best = 0;
    for (let j = 0; j < verts.length; j++) {
      const [ax, ay] = verts[j], [bx, by] = verts[(j + 1) % verts.length];
      const ex = bx - ax, ey = by - ay;
      const den = dx * ey - dy * ex;
      if (Math.abs(den) < 1e-9) continue;
      const s = (ax * ey - ay * ex) / den, q = (ax * dy - ay * dx) / den;
      if (s > 0 && q >= -1e-6 && q <= 1 + 1e-6) best = Math.max(best, s);
    }
    out[i] = best;
  }
  return out;
}
const ngon = (n, r, rot = -Math.PI / 2) => Array.from({ length: n }, (_, i) => [r * Math.cos(rot + i * TAU / n), r * Math.sin(rot + i * TAU / n)]);
const starV = (n, ro, ri) => Array.from({ length: n * 2 }, (_, i) => { const r = i % 2 ? ri : ro, a = -Math.PI / 2 + i * Math.PI / n; return [r * Math.cos(a), r * Math.sin(a)]; });
const SHAPES = [
  polyRadial([[-0.82, -0.82], [0.82, -0.82], [0.82, 0.82], [-0.82, 0.82]]),
  polyRadial(ngon(72, 0.95)),
  polyRadial(ngon(3, 1.18, -Math.PI / 2).map(([x, y]) => [x, y + 0.14])),
  polyRadial(starV(5, 1.15, 0.5)),
];
const C_COLS = 8, C_ROWS = 4, C_CELL = 200, C_X = 160, C_Y = 90;
const C_MORPHS = [7.0, 7.5, 8.0];
const C_ORIG = [[3.5, 1.5], [-1, 1.5], [-1, -1], [8, 1.5]];
const D_BL = [235, 505, 775, 1045];

function shapePath(ctx, rad, size) {
  const N = rad.length;
  ctx.beginPath();
  for (let i = 0; i < N; i++) {
    const th = (i / N) * TAU, r = rad[i] * size;
    if (i === 0) ctx.moveTo(r * Math.cos(th), r * Math.sin(th)); else ctx.lineTo(r * Math.cos(th), r * Math.sin(th));
  }
  ctx.closePath();
}

function sceneC(ctx, t) {
  ctx.fillStyle = INK; ctx.fillRect(0, 0, W, H);
  const tmp = new Float32Array(96);
  for (let r = 0; r < C_ROWS; r++) for (let c = 0; c < C_COLS; c++) {
    const cx = C_X + c * C_CELL + C_CELL / 2, cy = C_Y + r * C_CELL + C_CELL / 2;
    // guide dot
    ctx.fillStyle = 'rgba(140,136,128,0.35)'; ctx.fillRect(cx - 2, cy - 2, 4, 4);
    const dist = (o) => Math.hypot(c - o[0], r - o[1]);
    const ent = E.outBack(prog(t, 6.38 + dist(C_ORIG[0]) * 0.05, 6.38 + dist(C_ORIG[0]) * 0.05 + 0.38), 2.2);
    if (ent <= 0) continue;
    // which morph are we in
    let idx = 0, e = 0, rot = 0, punch = 0;
    for (let m = 0; m < C_MORPHS.length; m++) {
      const d0 = C_MORPHS[m] + dist(C_ORIG[m + 1]) * 0.035;
      const p = prog(t, d0, d0 + 0.32);
      if (p > 0) { idx = m; e = E.inOutCubic(p); punch = Math.sin(Math.PI * p); }
      rot += (Math.PI / 2) * E.outBack(p, 1.6);
    }
    let a = SHAPES[idx], b = SHAPES[Math.min(idx + 1, 3)];
    if (t < C_MORPHS[0]) { a = SHAPES[0]; b = SHAPES[0]; }
    for (let i = 0; i < 96; i++) tmp[i] = lerp(a[i], b[i], e);
    // collapse into baselines for the type scene
    const cp = E.inOutCubic(prog(t, 8.14 + c * 0.01, 8.36 + c * 0.01));
    const sx = lerp(1, 1.8, cp), sy = lerp(1, 0.035, cp);
    const y = lerp(cy, D_BL[r], cp);
    const stage = idx + (e > 0.5 ? 1 : 0);
    const accent = (c * 7 + r * 3 + stage) % 6 === 0;
    ctx.save();
    ctx.translate(cx, y);
    ctx.scale(sx, sy);
    ctx.rotate(rot * (1 - cp));
    const size = 60 * ent * (1 - 0.28 * punch);
    shapePath(ctx, tmp, size);
    ctx.fillStyle = accent && cp < 0.5 ? ACC : PAPER;
    ctx.fill();
    ctx.restore();
  }
  if (t < 8.14) label(ctx, '03', 'MORPH  ·  STAGGER  ·  OFFSET', C_X, 985, t, 6.7, PAPER);
}

// ======================================================================
// SCENE D — 8.5–10.5  kinetic type rows
// ======================================================================
const D_FS = 290, D_CAP = D_FS * 0.72;
const D_ROWS = [
  { word: 'KINETIC', dir: -1, v: 300, mode: 'bounce' },
  { word: 'WEIGHT', dir: 1, v: 260, mode: 'weight', stroke: true },
  { word: 'WIDTH', dir: -1, v: 240, mode: 'width' },
  { word: 'RHYTHM', dir: 1, v: 200, mode: 'kick', stroke: true },
];
const D_BEATS = [8.5, 9.0, 9.5, 10.0, 10.5];
const STRETCHES = ['extra-condensed', 'expanded', 'condensed', 'semi-expanded', 'extra-condensed'];

function sceneD(ctx, t) {
  ctx.fillStyle = PAPER; ctx.fillRect(0, 0, W, H);
  const lt = t - 8.5;
  const beatIdx = clamp(Math.floor(lt / 0.5), 0, 4);
  for (let ri = 0; ri < 4; ri++) {
    const row = D_ROWS[ri], bl = D_BL[ri];
    // baseline rule retracting
    const rp = E.inOutCubic(prog(t, 8.44 + ri * 0.04, 8.8 + ri * 0.04));
    if (rp < 1) { ctx.fillStyle = INK; ctx.fillRect(W * rp, bl - 3, W * (1 - rp), 6); }
    const rise = (1 - E.outExpo(prog(t, 8.44 + ri * 0.04, 8.84 + ri * 0.04))) * D_FS;
    let kicks = 0;
    for (const b of D_BEATS) if (b > 8.5) kicks += E.outExpo(prog(t, b, b + 0.4));
    const kickAmt = row.mode === 'kick' ? 420 : 140;
    const off = row.dir * (row.v * lt + kickAmt * kicks + 400 * E.outExpo(prog(t, 8.5, 9.0)));
    const stretch = row.mode === 'width' ? STRETCHES[beatIdx] : 'normal';
    const wBase = 900;
    // measure one unit = word + dot gap
    setFont(ctx, D_FS, wBase, DISP, stretch);
    const gap = 150;
    const unitW = tw(ctx, row.word) + gap;
    let x = ((off % unitW) + unitW) % unitW - unitW;
    ctx.save();
    if (rise > 0.5) { ctx.beginPath(); ctx.rect(0, bl - D_FS, W, D_FS + 3); ctx.clip(); }
    let li = 0;
    while (x < W + 40) {
      let cx = x;
      for (let i = 0; i < row.word.length; i++, li++) {
        const ch = row.word[i];
        let wg = wBase, dy = 0, sy = 1;
        if (row.mode === 'weight') wg = 520 + 380 * Math.sin(TAU * (cx / 1100 - lt * 1.4));
        if (row.mode === 'bounce') for (const b of D_BEATS) dy -= 70 * bump(t - b - i * 0.032, 0.3);
        if (row.mode === 'width') sy = 1 + 0.16 * Math.exp(-Math.max(0, lt - beatIdx * 0.5) * 14);
        setFont(ctx, D_FS, wg, DISP, stretch);
        const w = tw(ctx, ch);
        if (cx + w > -50 && cx < W + 50) {
          if (row.stroke) { ctx.strokeStyle = INK; ctx.lineWidth = 4; ctx.lineJoin = 'round'; }
          ctx.fillStyle = INK;
          glyph(ctx, ch, cx, bl, w, D_CAP, { dy: dy + rise, sy, stroke: row.stroke });
        }
        cx += w;
      }
      // separator dot
      const r = 30 * (1 + 0.35 * Math.exp(-((lt % 0.5)) * 10));
      ctx.fillStyle = ACC; ctx.beginPath(); ctx.arc(cx + gap / 2, bl - D_CAP / 2 + rise, r, 0, TAU); ctx.fill();
      x = cx + gap;
    }
    ctx.restore();
  }
  // chip label in the gutter between rows 1 and 2
  if (t > 8.75) {
    const full = '04   KINETIC TYPE  ·  VARIABLE AXES  ·  RHYTHM';
    const n = typedCount(full, t, 8.8, 48);
    setFont(ctx, 28, 400, MONO);
    const cw = tw(ctx, full.slice(0, n)) + 64;
    const open = E.outExpo(prog(t, 8.75, 9.0));
    ctx.fillStyle = INK; ctx.beginPath(); ctx.roundRect(80, 512, Math.max(56, cw) * open, 56, 28); ctx.fill();
    ctx.save(); ctx.beginPath(); ctx.rect(80, 512, cw * open, 56); ctx.clip();
    label(ctx, '04', 'KINETIC TYPE  ·  VARIABLE AXES  ·  RHYTHM', 110, 550, t, 8.8, PAPER, 28);
    ctx.restore();
  }
}

// ======================================================================
// SCENE E — 10.5–12.5  3D card ring
// ======================================================================
const E_N = 12, E_R = 980, E_CW = 320, E_CH = 440, E_F = 1500;
const E_TITLES = ['BRAND IDENT', 'UI MOTION', 'TITLE SEQ', 'KINETIC TYPE', 'PRODUCT 3D', 'LOOPS', 'DATA VIZ', 'SOCIAL CUTS', 'EXPLAINER', 'LIVE EVENT', 'MUSIC VIDEO', 'ONBOARDING'];
const E_ACC = new Set([1, 7]);
const E_STEPS = [11.0, 11.5, 12.0];

function sceneE(ctx, t) {
  ctx.fillStyle = INK; ctx.fillRect(0, 0, W, H);
  const entry = 150 * (1 - E.outExpo(prog(t, 10.4, 11.0)));
  let steps = 0;
  for (const b of E_STEPS) steps += E.outBack(prog(t, b, b + 0.36), 1.5);
  const rot = (entry - 30 * steps) * Math.PI / 180;
  const camD = lerp(2650, 2300, E.inOutCubic(prog(t, 10.5, 12.2)));
  const tilt = 0.2 + 0.05 * Math.sin((t - 10.5) * 1.3);
  const ct = Math.cos(tilt), st = Math.sin(tilt);
  const proj = (X, Y, Z) => {
    const y2 = Y * ct - Z * st, z2 = Y * st + Z * ct;
    const s = E_F / (z2 + camD);
    return { x: 960 + X * s, y: 470 + y2 * s, z: z2 };
  };
  const fly = E.inExpo(prog(t, 12.06, 12.4));
  const front = 3;
  const cards = [];
  for (let i = 0; i < E_N; i++) {
    const th = i * TAU / E_N + rot;
    const cx = E_R * Math.sin(th), cz = -E_R * Math.cos(th);
    const rx = Math.cos(th), rz = Math.sin(th);
    const c = [[-1, -1], [1, -1], [1, 1], [-1, 1]].map(([a, b]) => proj(cx + rx * a * E_CW / 2, b * E_CH / 2, cz + rz * a * E_CW / 2));
    cards.push({ i, c, z: (c[0].z + c[1].z + c[2].z + c[3].z) / 4 });
  }
  cards.sort((a, b) => b.z - a.z);
  for (const cd of cards) {
    let c = cd.c;
    if (cd.i === front && fly > 0) {
      const sc = 6.2, tw2 = E_CW * sc / 2, th2 = E_CH * sc / 2;
      const tgt = [[960 - tw2, 540 - th2], [960 + tw2, 540 - th2], [960 + tw2, 540 + th2], [960 - tw2, 540 + th2]];
      c = c.map((p, j) => ({ x: lerp(p.x, tgt[j][0], fly), y: lerp(p.y, tgt[j][1], fly) }));
    }
    const cross = (c[1].x - c[0].x) * (c[3].y - c[0].y) - (c[1].y - c[0].y) * (c[3].x - c[0].x);
    const faceFront = cross > 0;
    ctx.beginPath(); ctx.moveTo(c[0].x, c[0].y); for (let j = 1; j < 4; j++) ctx.lineTo(c[j].x, c[j].y); ctx.closePath();
    if (!faceFront) { ctx.fillStyle = SOFT; ctx.fill(); continue; }
    const acc = E_ACC.has(cd.i);
    ctx.fillStyle = acc ? ACC : PAPER; ctx.fill();
    // card content via affine from card space
    ctx.save();
    ctx.clip();
    ctx.transform((c[1].x - c[0].x) / E_CW, (c[1].y - c[0].y) / E_CW, (c[3].x - c[0].x) / E_CH, (c[3].y - c[0].y) / E_CH, c[0].x, c[0].y);
    ctx.fillStyle = INK;
    setFont(ctx, 92, 900); ctx.textBaseline = 'alphabetic';
    ctx.fillText(String(cd.i + 1).padStart(2, '0'), 22, 100);
    // mini motif, top-right
    ctx.save(); ctx.translate(254, 70);
    const mt = t * 2 + cd.i;
    ctx.fillStyle = acc ? INK : ACC;
    switch (cd.i % 5) {
      case 0: ctx.beginPath(); ctx.arc(0, 0, 30 + 4 * Math.sin(mt * 3), 0, TAU); ctx.fill(); break;
      case 1: for (let j = 0; j < 3; j++) { const h = 22 + 22 * (0.5 + 0.5 * Math.sin(mt * 3 + j)); ctx.fillRect(-30 + j * 22, 30 - h, 14, h); } break;
      case 2: ctx.rotate(mt); ctx.fillRect(-22, -22, 44, 44); break;
      case 3: ctx.lineWidth = 9; ctx.strokeStyle = acc ? INK : ACC; ctx.beginPath(); ctx.arc(0, 0, 26, mt, mt + 4.4); ctx.stroke(); break;
      case 4: ctx.rotate(-mt * 0.7); ctx.beginPath(); ctx.moveTo(0, -32); ctx.lineTo(28, 18); ctx.lineTo(-28, 18); ctx.closePath(); ctx.fill(); break;
    }
    ctx.restore();
    ctx.fillStyle = INK; ctx.fillRect(22, 366, 276, 3);
    setFont(ctx, 24, 700, MONO); ctx.fillText(E_TITLES[cd.i], 22, 412);
    ctx.restore();
    // depth shade
    const shade = clamp((cd.z + 400) / 1800) * 0.5 * (1 - fly);
    if (shade > 0.01) { ctx.fillStyle = `rgba(13,13,15,${shade})`; ctx.beginPath(); ctx.moveTo(c[0].x, c[0].y); for (let j = 1; j < 4; j++) ctx.lineTo(c[j].x, c[j].y); ctx.closePath(); ctx.fill(); }
  }
  if (fly < 0.2) label(ctx, '05', '3D SPACE  ·  CAMERA  ·  DEPTH', 960, 1010, t, 10.75, PAPER, 32, 'center');
}

// ======================================================================
// SCENE F — 12.5–14.5  parametric paths with trim
// ======================================================================
const F_KEYS = [[12.5, 3, 2], [13.0, 5, 4], [13.5, 1, 2], [14.0, 3, 4]];
const BASE_Y = 780, BASE_X0 = 260, BASE_X1 = 1660;
function fParams(t) {
  let a = F_KEYS[0][1], b = F_KEYS[0][2];
  for (let i = 1; i < F_KEYS.length; i++) {
    const e = E.inOutCubic(prog(t, F_KEYS[i][0], F_KEYS[i][0] + 0.32));
    a = lerp(a, F_KEYS[i][1], e); b = lerp(b, F_KEYS[i][2], e);
  }
  return { a, b, d: Math.PI / 2 + (t - 12.5) * 1.1 };
}
function sceneF(ctx, t) {
  ctx.fillStyle = PAPER; ctx.fillRect(0, 0, W, H);
  const { a, b, d } = fParams(t);
  const straight = E.inOutCubic(prog(t, 14.1, 14.42));
  const N = 700;
  const lines = [{ k: -1, col: INK }, { k: 1, col: INK }, { k: 0, col: ACC }];
  let head = null;
  for (const L of lines) {
    const trim = E.inOutCubic(prog(t, 12.4 + (L.k + 1) * 0.05, 13.05 + (L.k + 1) * 0.05));
    if (trim <= 0) continue;
    ctx.strokeStyle = L.col; ctx.lineWidth = lerp(10, 4, straight); ctx.lineCap = 'round'; ctx.lineJoin = 'round';
    ctx.beginPath();
    const n = Math.floor(N * trim);
    let px, py;
    for (let i = 0; i <= n; i++) {
      const s = (i / N) * TAU;
      const lx = 960 + 560 * Math.sin(a * s + d + L.k * 0.16), ly = 480 + 330 * Math.sin(b * s);
      const bx = lerp(BASE_X0, BASE_X1, i / N), by = BASE_Y;
      px = lerp(lx, bx, straight); py = lerp(ly, by, straight);
      if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
    }
    ctx.stroke();
    if (L.k === 0 && trim < 1) head = [px, py];
  }
  if (head) { ctx.fillStyle = ACC; ctx.beginPath(); ctx.arc(head[0], head[1], 17, 0, TAU); ctx.fill(); }
  if (straight < 0.5) {
    label(ctx, '06', 'PARAMETRIC PATHS  ·  TRIM', 120, 905, t, 12.6, INK);
    if (t > 12.9) {
      setFont(ctx, 28, 400, MONO); ctx.fillStyle = GRAY;
      const tr = Math.round(100 * E.inOutCubic(prog(t, 12.5, 13.15)));
      ctx.fillText(`a:b  ${a.toFixed(2)} : ${b.toFixed(2)}     phase  ${(d % TAU).toFixed(2)}     trim end  ${tr}%`, 120, 955);
    }
  }
}

// ======================================================================
// SCENE G — 14.5–16.5  data in motion
// ======================================================================
const G_N = 12, G_SLOT = (BASE_X1 - BASE_X0) / G_N, G_BW = 64;
const G_VALS = Array.from({ length: G_N }, (_, i) => 0.14 + 0.86 * rnd(i, 11));
const G_RANK = (() => { const idx = G_VALS.map((v, i) => i).sort((p, q) => G_VALS[p] - G_VALS[q]); const r = []; idx.forEach((bi, j) => (r[bi] = j)); return r; })();
const G_TOP = G_RANK.indexOf(G_N - 1);
const slotX = j => BASE_X0 + (j + 0.5) * G_SLOT;

function sceneG(ctx, t) {
  ctx.fillStyle = PAPER; ctx.fillRect(0, 0, W, H);
  ctx.fillStyle = INK; ctx.fillRect(BASE_X0, BASE_Y - 2, BASE_X1 - BASE_X0, 4);
  const sorted = [];
  for (let i = 0; i < G_N; i++) {
    const h = G_VALS[i] * 400 * spring(t - 14.42 - i * 0.035, 2.4, 0.42);
    const sp = E.inOutCubic(prog(t, 15.0 + Math.abs(i - G_RANK[i]) * 0.012, 15.4 + Math.abs(i - G_RANK[i]) * 0.012));
    const x = lerp(slotX(i), slotX(G_RANK[i]), sp);
    const lift = G_RANK[i] !== i ? 34 * Math.sin(Math.PI * sp) : 0;
    ctx.fillStyle = INK;
    ctx.fillRect(x - G_BW / 2, BASE_Y - 2 - h - lift, G_BW, h);
    if (i === G_TOP) {
      const ah = h * E.outExpo(prog(t, 16.0, 16.3));
      ctx.fillStyle = ACC; ctx.fillRect(x - G_BW / 2, BASE_Y - 2 - ah - lift, G_BW, ah);
    }
    sorted[G_RANK[i]] = G_VALS[i] * 400;
  }
  // line chart over the sorted bars
  const lp = E.inOutCubic(prog(t, 15.5, 15.95));
  if (lp > 0) {
    ctx.strokeStyle = INK; ctx.lineWidth = 4; ctx.lineJoin = 'round'; ctx.lineCap = 'round';
    const pts = sorted.map((h, j) => [slotX(j), BASE_Y - h - 50]);
    const span = lp * (G_N - 1);
    ctx.beginPath(); ctx.moveTo(...pts[0]);
    for (let j = 1; j <= Math.floor(span); j++) ctx.lineTo(...pts[j]);
    const f = span - Math.floor(span);
    if (Math.floor(span) < G_N - 1) { const a = pts[Math.floor(span)], b = pts[Math.floor(span) + 1]; ctx.lineTo(lerp(a[0], b[0], f), lerp(a[1], b[1], f)); }
    ctx.stroke();
    for (let j = 0; j < G_N; j++) {
      const pop = E.outBack(prog(t, 15.5 + (j / (G_N - 1)) * 0.45, 15.5 + (j / (G_N - 1)) * 0.45 + 0.18), 2.5);
      if (pop <= 0) continue;
      ctx.fillStyle = j === G_N - 1 && t > 16.0 ? ACC : PAPER; ctx.beginPath(); ctx.arc(pts[j][0], pts[j][1], 10 * pop, 0, TAU); ctx.fill();
      ctx.lineWidth = 4; ctx.stroke();
    }
  }
  // odometer
  const str = '+2,480%';
  setFont(ctx, 170, 900);
  const cellW = tw(ctx, '0'), LH = 190, oy = 300;
  let x = BASE_X0, di = 0;
  ctx.save(); ctx.beginPath(); ctx.rect(BASE_X0 - 20, oy - 150, 1000, 190); ctx.clip();
  for (const ch of str) {
    ctx.fillStyle = INK;
    if (ch >= '0' && ch <= '9') {
      const p = E.outExpo(prog(t, 14.42 + di * 0.07, 15.4 + di * 0.07));
      const f = +ch + 10 * (di + 2) * (1 - p);
      const base = Math.floor(f), frac = f - base;
      ctx.fillText(String(base % 10), x, oy - frac * LH);
      ctx.fillText(String((base + 1) % 10), x, oy + (1 - frac) * LH);
      x += cellW; di++;
    } else {
      const p = E.outExpo(prog(t, 14.42, 14.8));
      ctx.fillText(ch, x, oy + (1 - p) * LH);
      x += tw(ctx, ch);
    }
  }
  ctx.restore();
  typeLine(ctx, 'MORE FRAMES SHIPPED THAN LAST YEAR', BASE_X0 + 6, oy + 60, t, 14.6, { size: 28, color: GRAY, cps: 60, caret: false });
  label(ctx, '07', 'DATA IN MOTION  ·  SORT  ·  ROLL', BASE_X0, 860, t, 14.9, INK);
}

// ======================================================================
// SCENE H — 16.5–21  generative tile system (keeps running inside the mosaic)
// ======================================================================
const T_S = 120, T_C = 16, T_R = 9;
function sceneH(ctx, t) {
  ctx.fillStyle = INK; ctx.fillRect(0, 0, W, H);
  for (let r = 0; r < T_R; r++) for (let c = 0; c < T_C; c++) {
    if (r === 7 && c >= 1 && c <= 7) continue;
    const id = 500 + r * T_C + c;
    const ty = rnd(id, 1);
    const d = (c + r) * 0.014;
    const ent = E.outBack(prog(t, 16.28 + d, 16.28 + d + 0.32), 1.8);
    if (ent <= 0) continue;
    let turns = Math.floor(rnd(id, 2) * 4);
    for (let b = 17.0; b < 21.0; b += 0.5) turns += E.outBack(prog(t, b + d, b + d + 0.3), 1.4);
    ctx.save();
    ctx.translate(c * T_S + T_S / 2, r * T_S + T_S / 2);
    ctx.rotate(turns * Math.PI / 2);
    ctx.scale(ent, ent);
    const hs = T_S / 2;
    ctx.fillStyle = PAPER;
    ctx.beginPath();
    if (ty < 0.3) { ctx.moveTo(-hs, -hs); ctx.arc(-hs, -hs, T_S, 0, Math.PI / 2); ctx.closePath(); }
    else if (ty < 0.5) { ctx.arc(0, -hs, hs, 0, Math.PI); ctx.closePath(); }
    else if (ty < 0.62) { ctx.arc(0, 0, 30, 0, TAU); }
    else if (ty < 0.8) { ctx.moveTo(-hs, -hs); ctx.lineTo(hs, -hs); ctx.lineTo(-hs, hs); ctx.closePath(); }
    else if (ty < 0.9) { ctx.fillStyle = ACC; ctx.moveTo(-hs, -hs); ctx.arc(-hs, -hs, T_S, 0, Math.PI / 2); ctx.closePath(); }
    else { ctx.rect(-hs, -6, T_S, 12); }
    ctx.fill();
    ctx.restore();
  }
  label(ctx, '08', 'SYSTEMS  ·  GENERATIVE GRIDS', 150, 912, t, 16.7, PAPER, 30);
}

// ======================================================================
// SCENE I — 18–21  the reel is the work: zoom out to a live mosaic, shuffle, flip
// ======================================================================
const M_G = 16, M_M = 48;
const M_CW = (W - 2 * M_M - 2 * M_G) / 3, M_CH = M_CW * 9 / 16;
const M_OY = (H - (3 * M_CH + 2 * M_G)) / 2;
const M_ITEMS = [
  { fn: sceneA, a: 0.9, home: [0, 0] }, { fn: sceneB, a: 4.6, home: [1, 0] }, { fn: sceneC, a: 6.6, home: [2, 0] },
  { fn: sceneD, a: 8.6, home: [0, 1] }, { fn: sceneH, a: null, home: [1, 1] }, { fn: sceneE, a: 10.55, home: [2, 1] },
  { fn: sceneF, a: 12.6, home: [0, 2] }, { fn: sceneG, a: 14.6, home: [1, 2] }, { fn: sceneA, a: 2.3, home: [2, 2] },
];
const M_MOVES = [
  { t: 19.0, sel: p => p[1] === 0, d: [1, 0] },
  { t: 19.5, sel: p => p[0] === 1, d: [0, 1] },
  { t: 20.0, sel: p => p[1] === 2, d: [-1, 0] },
];
const wrap3 = v => ((v % 3) + 3) % 3;

function sceneI(ctx, t) {
  ctx.fillStyle = INK; ctx.fillRect(0, 0, W, H);
  const zoom = E.inOutExpo(prog(t, 18.0, 18.62));
  const S = lerp(W / M_CW, 1, zoom);
  const close = E.inOutCubic(prog(t, 20.8, 21.0));
  const g = lerp(M_G, 0, close), mx = lerp(M_M, 0, close);
  const cw = (W - 2 * mx - 2 * g) / 3, ch = lerp(M_CH, (H - 2 * g) / 3, close), oy = lerp(M_OY, 0, close);
  const rad = lerp(10, 0, close);
  ctx.save();
  ctx.translate(960, 540); ctx.scale(S, S); ctx.translate(-960, -540);
  const cellX = col => mx + col * (cw + g), cellY = row => oy + row * (ch + g);
  ctx.save(); ctx.beginPath(); ctx.rect(mx, oy, 3 * cw + 2 * g, 3 * ch + 2 * g); ctx.clip();
  M_ITEMS.forEach((it, idx) => {
    // logical positions after each move; float position now
    let L = it.home.slice(), P = it.home.slice();
    for (const mv of M_MOVES) {
      if (mv.sel(L)) {
        const e = E.inOutExpo(prog(t, mv.t, mv.t + 0.36));
        P = [P[0] + mv.d[0] * e, P[1] + mv.d[1] * e];
        L = [wrap3(L[0] + mv.d[0]), wrap3(L[1] + mv.d[1])];
      }
    }
    const fx = ((P[0] % 3) + 3) % 3, fy = ((P[1] % 3) + 3) % 3;
    const dist = Math.hypot(L[0] - 1, L[1] - 1);
    const fp = prog(t, 20.25 + dist * 0.16 + idx * 0.012, 20.25 + dist * 0.16 + idx * 0.012 + 0.24);
    const flipS = Math.abs(Math.cos(Math.PI * fp));
    const back = fp > 0.5;
    const lt = it.a === null ? t : it.a + ((t - 18.0) % 1.5 + 1.5) % 1.5;
    for (const ox of [0, -3, 3]) for (const oyy of [0, -3, 3]) {
      const col = fx + ox, row = fy + oyy;
      if (col <= -1 || col >= 3 || row <= -1 || row >= 3) continue;
      const x = cellX(col), y = cellY(row);
      ctx.save();
      ctx.translate(x + cw / 2, y + ch / 2); ctx.scale(flipS, 1); ctx.translate(-cw / 2, -ch / 2);
      ctx.beginPath(); ctx.roundRect(0, 0, cw, ch, rad); ctx.clip();
      if (back) { ctx.fillStyle = ACC; ctx.fillRect(0, 0, cw, ch); }
      else { ctx.scale(cw / W, ch / H); it.fn(ctx, lt); }
      ctx.restore();
    }
  });
  ctx.restore();
  ctx.restore();
}

// ======================================================================
// SCENE J — 21–25  end card: STUDIO.  (the period comes home)
// ======================================================================
const J_X = 150, J_BL = 560, J_FS = 300, J_RULE = 650, J_BR = 24;
function sceneJ(ctx, t) {
  ctx.fillStyle = INK; ctx.fillRect(0, 0, W, H);
  const word = STUDIO;
  setFont(ctx, J_FS, 900);
  const fullW = tw(ctx, word);
  const perX = J_X + fullW + 22 + J_BR;
  // type rises out of its baseline, weight swelling up
  ctx.save(); ctx.beginPath(); ctx.rect(0, J_BL - J_FS, W, J_FS + 4); ctx.clip();
  let x = J_X;
  for (let i = 0; i < word.length; i++) {
    const p = E.outExpo(prog(t, 21.05 + i * 0.05, 21.65 + i * 0.05));
    const wg = lerp(200, 900, E.outCubic(prog(t, 21.05 + i * 0.05, 21.75 + i * 0.05)));
    setFont(ctx, J_FS, 900);
    const slot = tw(ctx, word.slice(0, i + 1)) - tw(ctx, word.slice(0, i));
    setFont(ctx, J_FS, wg);
    const w = tw(ctx, word[i]);
    const ripple = -26 * bump(t - 24.0 - (word.length - 1 - i) * 0.035, 0.26);
    ctx.fillStyle = PAPER;
    glyph(ctx, word[i], x + (slot - w) / 2, J_BL, w, J_FS * 0.72, { dy: (1 - p) * J_FS + ripple });
    x += slot;
  }
  ctx.restore();
  // ball: rolls the rule out, waits, hops into the period
  const r0 = J_X + J_BR, r1 = 1770 - J_BR;
  const roll = E.inOutCubic(prog(t, 21.45, 22.35));
  const bx0 = lerp(r0, r1, roll);
  ctx.fillStyle = RULE; ctx.fillRect(J_X, J_RULE, Math.max(0, bx0 - J_X), 2);
  if (t >= 23.5) ctx.fillRect(J_X, J_RULE, r1 - J_X, 2);
  let bx = bx0, byb = J_RULE, sx = 1, sy = 1, rot = 0;
  const stopSq = 0.18 * bump(t - 22.35, 0.16);
  const ant = 0.3 * E.inOutCubic(prog(t, 23.36, 23.5)) * (1 - prog(t, 23.5, 23.52));
  const u = prog(t, 23.52, 24.0);
  if (t >= 23.5) {
    bx = lerp(r1, perX, u);
    byb = lerp(J_RULE, J_BL, u) - 300 * 4 * u * (1 - u);
    const vx = (perX - r1) / 0.48, vy = (J_BL - J_RULE - 300 * 4 * (1 - 2 * u)) / 0.48;
    const s = clamp(Math.hypot(vx, vy) / 5200, 0, 0.4);
    if (u < 1) { sx = 1 + s; sy = 1 - s * 0.55; rot = Math.atan2(vy, vx); }
  }
  const land = 0.45 * bump(t - 24.0, 0.1);
  const squash = Math.max(stopSq, ant, land);
  if (squash > 0.01) ellipseBall(ctx, bx, byb - J_BR * (1 - squash), J_BR * (1 + squash * 0.8), J_BR * (1 - squash), 0, ACC);
  else ellipseBall(ctx, bx, byb - J_BR, J_BR * sx, J_BR * sy, rot, ACC);
  // credits
  typeLine(ctx, 'MOTION STUDIO  —  REEL 2026', J_X + 4, 735, t, 21.75, { size: 40, wght: 700, color: PAPER, cps: 44 });
  typeLine(ctx, 'KINETIC TYPE  ·  3D  ·  SYSTEMS  ·  DATA  ·  IDENTITY', J_X + 4, 795, t, 22.45, { size: 30, color: GRAY, cps: 56 });
  typeLine(ctx, '25 SECONDS  ·  1,500 FRAMES  ·  ZERO KEYFRAMES  —  EVERY FRAME IS f(t)', J_X + 4, 845, t, 23.05, { size: 30, color: GRAY, cps: 64 });
  // accent iris collapsing into the ball on the drop
  const ir = lerp(2400, J_BR, E.outExpo(prog(t, 21.0, 21.5)));
  if (ir > J_BR + 0.5) { ctx.fillStyle = ACC; ctx.beginPath(); ctx.arc(r0, J_RULE - J_BR, ir, 0, TAU); ctx.fill(); }
}

// ======================================================================
// transitions + timeline
// ======================================================================
const buf = [document.createElement('canvas'), document.createElement('canvas')];
for (const b of buf) { b.width = W; b.height = H; }

function slats(ctx, t, from, to, t0, t1, n, w) {
  from(ctx, t);
  const dur = 0.2, stg = (t1 - t0 - dur) / (n - 1);
  ctx.save(); ctx.beginPath();
  for (let i = 0; i < n; i++) {
    const h = H * E.inOutCubic(prog(t, t0 + i * stg, t0 + i * stg + dur));
    if (h > 0) ctx.rect(i * w, 0, w + 0.5, h);
  }
  ctx.clip(); to(ctx, t); ctx.restore();
}

function whip(ctx, t, from, to, t0, t1) {
  const mid = (t0 + t1) / 2;
  const a = buf[0].getContext('2d'), b = buf[1].getContext('2d');
  a.setTransform(1, 0, 0, 1, 0, 0); b.setTransform(1, 0, 0, 1, 0, 0);
  from(a, t); to(b, t);
  const pan = τ => (τ < mid ? 0.5 * W * E.inExpo(prog(τ, t0, mid)) : W * 0.5 + 0.5 * W * E.outExpo(prog(τ, mid, t1)));
  ctx.fillStyle = '#000'; ctx.fillRect(0, 0, W, H);
  ctx.save(); ctx.globalCompositeOperation = 'lighter';
  const N = 14, shutter = 1 / 90;
  ctx.globalAlpha = 1 / N;
  for (let k = 0; k < N; k++) {
    const p = pan(t - shutter * (k / (N - 1) - 0.5));
    ctx.drawImage(buf[0], -p, 0);
    ctx.drawImage(buf[1], W - p, 0);
  }
  ctx.restore();
}

function render(ctx, t) {
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over';
  ctx.textAlign = 'left'; ctx.textBaseline = 'alphabetic';
  if (t < 4.0) return sceneA(ctx, t);
  if (t < 4.34) {
    sceneA(ctx, t);
    const R = lerp(46, 2400, E.outQuart(prog(t, 4.0, 4.34)));
    ctx.save(); ctx.beginPath(); ctx.arc(HOPS[3].x1, FLOOR - 46, R, 0, TAU); ctx.clip(); sceneB(ctx, t); ctx.restore();
    return;
  }
  if (t < 6.15) return sceneB(ctx, t);
  if (t < 6.45) return slats(ctx, t, sceneB, sceneC, 6.15, 6.45, 12, 160);
  if (t < 8.44) return sceneC(ctx, t);
  if (t < 10.36) return sceneD(ctx, t);
  if (t < 10.64) return whip(ctx, t, sceneD, sceneE, 10.36, 10.64);
  if (t < 12.4) return sceneE(ctx, t);
  if (t < 14.42) return sceneF(ctx, t);
  if (t < 16.2) return sceneG(ctx, t);
  if (t < 16.5) return slats(ctx, t, sceneG, sceneH, 16.2, 16.5, 16, 120);
  if (t < 18.0) return sceneH(ctx, t);
  if (t < 21.0) return sceneI(ctx, t);
  return sceneJ(ctx, t);
}

// ---------------------------------------------------------------- entry
const canvas = document.getElementById('c');
const ctx = canvas.getContext('2d');
window.ready = Promise.all([
  document.fonts.load(`900 100px ${DISP}`), document.fonts.load(`100 100px ${DISP}`),
  document.fonts.load(`400 20px ${MONO}`), document.fonts.load(`700 20px ${MONO}`),
]).then(() => document.fonts.ready);
window.seek = async (t) => { await window.ready; render(ctx, Math.min(t, DUR - 1e-6)); };
window.DUR = DUR;

// preview mode only: ?play drives seek from rAF, ?t=12.3 shows a single frame
const q = new URLSearchParams(location.search);
if (q.has('t')) window.seek(+q.get('t'));
if (q.has('play')) {
  window.ready.then(() => {
    const t0 = performance.now();
    const loop = () => { render(ctx, ((performance.now() - t0) / 1000) % DUR); requestAnimationFrame(loop); };
    requestAnimationFrame(loop);
  });
}
