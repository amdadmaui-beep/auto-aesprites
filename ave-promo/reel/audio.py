# AVE "more heat" reel — original beat (120 BPM, D dorian) + sound design, cued from cues.js.
# Reuses the V3 promo's instruments (../film/audio.py, ../film/score_v3.py).
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); FILM = os.path.join(HERE, '..', 'film')
a = open(os.path.join(FILM, 'audio.py')).read(); a = a[:a.index("exec(open(os.path.join(ROOT, 'score_v3.py'))")]
a = a.replace("ROOT = os.path.dirname(os.path.abspath(__file__))", "ROOT = HERE")
exec(a)
b = open(os.path.join(FILM, 'score_v3.py')).read(); exec(b[:b.index('def score_v3():')])

# 1 · heat (0–1.75): pixel glitches, bell motif, riser into the 99 impact
for k in range(14): tickp(.02 + k * .024, .03 * (1 - k / 16), 4000 + 300 * (k % 5), (-1) ** k * .4)
kick2(0.0, .35); pad2(0.0, 1.9, ['D3', 'A3', 'E4'], .03, 800)
for i, (dt, n) in enumerate(MOTIF[:5]): bell(.5 + dt * .5, n, .05, -.3 + .15 * i, .4)
noiseriser(C['roll'], C['hit99'], .09)
t = tv(C['hit99'] - C['roll']); add(sfx, C['roll'], np.sin(2 * np.pi * np.cumsum(300 * 4 ** (t / t[-1])) / SR) * (t / t[-1]) ** 2 * .5, .05)   # gauge climbing
for k in range(12): tick(C['roll'] + k * .075, .02 + .002 * k, .2)                                                                     # number rolling
mask(C['cap1'], .05); mask(C['cap2'], .06, .1)
H = C['hit99']; kick2(H, .5); subdrop(H, .28, 1.0); crash(H, .06); stab(H, ['D3', 'F3', 'A3', 'C4', 'E4'], .07, 0, .3); hit(H, .18)
whoosh(C['morph'] - .05, .4, .12, 400, 4000, -.4, .4, .6); mask(C['card1'] - .02, .07)
# 2 · cards (2.0–6.5): full groove, a new colour every bar or half bar
for b0 in (2.0, 4.0):
    bar_groove(b0, 6.25, K_FUNK, hats=2, motif=MOTIF if b0 == 2.0 else [(dt, up(n)) for dt, n in ANSWER], mg=.045, shk=True, bg=.14)
bar_groove(6.0, 6.25, K_FUNK, hats=2, stabs=False, bg=.14)
for s in (3.25, 5.25): stutter(s)
thump(C['punch1'], .14, 160, 60, .08); tone(C['punch1'], 880, .04)                                     # colour drops in on the punchline
for T in (C['card2'], C['card3'], C['card4']): whoosh(T - .12, .26, .2, 600, 7000, .7, -.6, .55); click(T, .1, 3000)
for i in range(5): tone(C['stars'] + i * .1, 1318.5 * 1.122 ** i, .04, -.4 + .2 * i, .05)               # stars fill
noiseriser(C['push'] - .3, C['white'], .08)
# hard cut to white: the band stops, the tagline slams
W = C['white']
i0, i1 = int((C['push'] + .05) * SR), int(W * SR); music[i0:i1] *= np.linspace(1, .15, i1 - i0)[:, None]; music[i1:] = 0
kick2(W, .5); subdrop(W, .26, 1.2); crash(W, .05)
scrub(W + .02, C['stop'] - .02, .05); click(C['stop'], .2, 2600); tone(C['stop'] + .02, 1760, .04)
thump(C['slam'], .22, 150, 55, .1); thump(C['slam'] + .07, .16, 150, 55, .1)
whoosh(C['purpose'] - .02, .3, .07, 1200, 6000, -.3, .3, .4); whoosh(C['purpose'] + .14, .3, .06, 2000, 8000, -.5, .5, .5)
# groove returns, filtered, for the lockup
bar_groove(7.0, 7.75, K_BUILD, hats=1, stabs=False, bassOn=True, bg=.1)
L0 = C['lock']; whoosh(L0 - .1, .35, .1, 3000, 600, 0, 0, .4); mask(C['logo'], .07)
bar_groove(7.75, 9.25, K_BUILD, hats=1, stabs=True, motif=[(dt, n) for dt, n in MOTIF], mg=.04, bg=.11)
for k, ch_ in enumerate('SAMPLE'): click(C['type'] + k * .075, .09, 3600 + 200 * k, .1)
whoosh(C['send'] - .02, .35, .1, 800, 9000, -.2, .6, .4); tone(C['send'] + .05, 1760, .05); tone(C['send'] + .1, 2637, .04)
Sg = C['send'] + .2; kick2(Sg, .4); subdrop(Sg, .2, 1.2)
for i, n in enumerate(['D5', 'F5', 'A5', 'E6']): bell(Sg + i * .03, n, .06, -.3 + .2 * i, 1.0, .5)
stab(Sg, ['D3', 'A3', 'C4', 'E4'], .05, 0, .4)

# sidechain + sends (same as the promo)
pump = np.ones(N, np.float32)
for kt in kicks:
    i = int(kt * SR); n = int(.22 * SR); j = min(N, i + n)
    if j > i: pump[i:j] = np.minimum(pump[i:j], .55 + .45 * (np.arange(j - i) / n) ** .7)
music[:] *= pump[:, None]
Ec = np.zeros_like(echo); d1 = int(3 * S16 * SR); src_ = lp(echo.mean(1), 5000)
for k in range(1, 6):
    d = d1 * k
    if d < N: Ec[d:, k % 2] += src_[:N - d] * (.42 ** k)
music[:] += Ec
ir_t = tv(.9); ir = rng.standard_normal(len(ir_t)) * np.exp(-ir_t / .22); ir /= np.sqrt((ir ** 2).sum())
for c in (0, 1): music[:, c] += fftconvolve(verb[:, c], ir, 'full')[:N].astype(np.float32) * .5
mix = .55 * music + sfx
fo = int(.35 * SR); mix[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 1.5
mix = np.tanh(mix * 1.1) / 1.1
os.makedirs(os.path.join(HERE, 'build'), exist_ok=True)
y = np.clip(mix, -1, 1); w = wave.open(os.path.join(HERE, 'build', 'mix_raw.wav'), 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((y * 32767).astype(np.int16).tobytes()); w.close()
print('ok', float(np.abs(mix).max()))
