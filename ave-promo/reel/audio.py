# AVE "more heat" reel — original music and sound design placed on the reference's measured hit map
# (sub hits, hats, gaps, cuts), plus Jane Perry voiceover. Instruments reused from ../film.
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); FILM = os.path.join(HERE, '..', 'film')
a = open(os.path.join(FILM, 'audio.py')).read(); a = a[:a.index("exec(open(os.path.join(ROOT, 'score_v3.py'))")]
a = a.replace("ROOT = os.path.dirname(os.path.abspath(__file__))", "ROOT = HERE")
exec(a)
b = open(os.path.join(FILM, 'score_v3.py')).read(); exec(b[:b.index('def score_v3():')])
CUTS = [C['card1'], C['card2'], C['card3'], C['card4'], C['white']]
def b808(t0, d, n, g=.32, glide=0.):
    f = nf(n); t = tv(d + .08); ff = f * 2 ** (glide * np.exp(-t / .06) / 12)
    x = np.tanh(2.4 * np.sin(2 * np.pi * np.cumsum(ff) / SR)) * np.exp(-t / max(.12, d * .9))
    x *= np.minimum(1, t / .003) * np.clip((d + .06 - t) / .05, 0, 1); add(music, t0, lp(x, 420), g)
# 808 line on every measured sub hit (own notes, D minor)
RIFF = ['D1', 'D1', 'F1', 'D1', 'A1', 'G1', 'F1', 'C2']
B = C['BEATS']
SUBWIN = [(0.43, 1.30), (1.70, 3.55), (3.733, 4.0), (4.34, 4.62), (4.86, 5.2), (5.98, 6.92), (7.30, 7.95), (8.0, 8.3)]   # where the reference's bass plays
for i, t0 in enumerate(B):
    if not any(a0 - .02 <= t0 < a1 for a0, a1 in SUBWIN): continue
    end = min(a1 for a0, a1 in SUBWIN if a0 - .02 <= t0 < a1)
    d = min((B[i + 1] - t0) if i + 1 < len(B) else .5, end - t0)
    b808(t0, min(d, .45), RIFF[i % 8], .26, 5 if i % 8 == 0 else 0)
# drums: kick on the heavy hits, snare/hat transients on the measured high-band hits
for t0 in [0.51, 1.70, 2.08, 2.94, 3.733, 4.40, 4.90, 5.867, 6.18, 6.54, 7.30, 7.52, 7.78, 8.01]: kick2(t0, .42)
for t0 in C['HATS']: snare(t0, .07, .3); hat2(t0 + .06, .02, .3)
for t0 in np.arange(1.70, 5.6, .12): hat2(t0, .012 if int(round(t0 / .12)) % 2 else .02, -.25)
# melody: bell motif over the heat opening and the white ending
for i, (dt, n) in enumerate(MOTIF): bell(.2 + dt * .6, n, .05, -.3 + .1 * i, .45)
for i, (dt, n) in enumerate(ANSWER): bell(5.95 + dt * .6, n, .045, -.3 + .1 * i, .5)
pad2(0.0, 1.7, ['D3', 'A3', 'E4'], .03, 900); pad2(5.867, 9.2, ['D3', 'F3', 'A3', 'C4', 'E4'], .03, 1200, .3, .8)
for t0 in (1.70, 2.94, 3.733, 4.40, 4.90): stab(t0, ['D3', 'F3', 'A3', 'C4', 'E4'], .05, 0, .2)
# builds into every colour cut, impact + whoosh on the cut
for a0, c in [(1.30, 1.70), (3.45, 3.733), (4.22, 4.40), (5.55, 5.867)]: noiseriser(a0, c, .07)
for c in CUTS:
    hit(c, .16); crash(c, .045); whoosh(c - .08, .2, .18, 500, 8000, -.6, .6, .7)
# swishes on the fast cuts inside the card, ticks as the number rolls, glitch on the pixel opening
for st, *_ in C['SHOTS']:
    if all(abs(st - c) > .02 for c in CUTS): whoosh(st - .05, .12, .09, 1500, 9000, .4, -.4, .6); click(st, .06, 3800, .2)
for k in range(10): tickp(.02 + k * .022, .03 * (1 - k / 12), 4200 + 400 * (k % 4), (-1) ** k * .4)
for k in range(9): tick(C['roll'] + k * .037, .025, .2)
mask(C['flash'], .06)
# white ending: playhead scrub, slam, highlighter, logo, typing, send
scrub(C['white'] + .02, C['stop'] - .02, .045); click(C['stop'], .16, 2600)
thump(C['slam'], .2, 150, 55, .1); thump(C['slam'] + .07, .14, 150, 55, .1)
whoosh(C['purpose'] + .1, .3, .07, 1500, 8000, -.5, .5, .5)
whoosh(C['logo'] - .05, .3, .1, 3000, 600, 0, 0, .4); mask(C['logo'] + .05, .07)
for k in range(6): click(C['type'] + k * .075, .09, 3600 + 200 * k, .1)
whoosh(C['send'] - .02, .3, .1, 800, 9000, -.2, .6, .4); tone(C['send'] + .05, 1760, .05); tone(C['send'] + .1, 2637, .04)
Sg = C['send'] + .15
for i, n in enumerate(['D5', 'F5', 'A5', 'E6']): bell(Sg + i * .03, n, .055, -.3 + .2 * i, 1.0, .5)
# the reference's gaps: the band drops out right before the blue cut, before white, and as the logo lands
gate = np.ones(N, np.float32)
for g0, g1 in [(3.98, 4.17), (5.40, 5.60), (6.93, 7.28)]:
    i0, i1 = int(g0 * SR), int(g1 * SR); f = int(.01 * SR); gate[i0:i1] = .08; gate[i0:i0 + f] = np.linspace(1, .08, f); gate[i1 - f:i1] = np.linspace(.08, 1, f)
# sidechain + sends
pump = np.ones(N, np.float32)
for kt in kicks:
    i = int(kt * SR); n = int(.18 * SR); j = min(N, i + n)
    if j > i: pump[i:j] = np.minimum(pump[i:j], .6 + .4 * (np.arange(j - i) / n) ** .7)
music[:] *= (pump * gate)[:, None]
Ec = np.zeros_like(echo); d1 = int(.18 * SR); src_ = lp(echo.mean(1), 5000)
for k in range(1, 5):
    d = d1 * k
    if d < N: Ec[d:, k % 2] += src_[:N - d] * (.4 ** k)
music[:] += Ec
ir_t = tv(.9); ir = rng.standard_normal(len(ir_t)) * np.exp(-ir_t / .22); ir /= np.sqrt((ir ** 2).sum())
for c in (0, 1): music[:, c] += fftconvolve(verb[:, c], ir, 'full')[:N].astype(np.float32) * .5
# voice (Jane Perry): natural speed; only the pause inside line 6 is shortened
def rv(p):
    w = wave.open(p); return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
VOD = os.path.join(HERE, 'vo')
def vline(i, t0, cut=None):
    x = rv(os.path.join(VOD, f'r{i}.wav')); x = hp(x, 90, 2); x = x + .22 * bp(x, 2500, 6500)
    if cut: a0, a1 = int(cut[0] * SR), int(cut[1] * SR); x = np.concatenate([x[:a0], x[a1:]])
    on = np.where(np.abs(x) > .015)[0][0]; x = x[on - int(.01 * SR):]; x[:480] *= np.linspace(0, 1, 480); x[-2400:] *= np.linspace(1, 0, 2400)
    add(vox, t0 - .01, x, 1.0)
vline(1, 0.15); vline(2, 1.78); vline(3, 3.78); vline(4, 4.48); vline(5, 5.06); vline(6, 5.98, (1.03, 1.18)); vline(7, 7.78)
vn = .32 / (np.percentile(np.abs(vox[np.abs(vox).max(1) > 1e-3]).max(1), 99) + 1e-9)
envv = np.abs(vox).max(1); k = int(.03 * SR); envv = np.sqrt(np.convolve(envv ** 2, np.ones(k) / k, 'same'))
act = np.clip(envv / .02, 0, 1); gg = np.zeros_like(act); s_ = 0; ac, rc = np.exp(-1 / (.02 * SR)), np.exp(-1 / (.25 * SR))
for i in range(len(act)):
    v = act[i]; c = ac if v > s_ else rc; s_ = c * s_ + (1 - c) * v; gg[i] = s_
mix = .55 * music * (1 - .45 * gg)[:, None] + sfx * (1 - .25 * gg)[:, None] + vox * vn
fo = int(.3 * SR); mix[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 1.5
mix = np.tanh(mix * 1.1) / 1.1
os.makedirs(os.path.join(HERE, 'build'), exist_ok=True)
y = np.clip(mix, -1, 1); w = wave.open(os.path.join(HERE, 'build', 'mix_raw.wav'), 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((y * 32767).astype(np.int16).tobytes()); w.close()
# overlap check for the voice lines
print('ok peak', float(np.abs(mix).max()))
