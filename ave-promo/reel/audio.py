# AVE "more heat" reel — approved music draft A + sound design on the picture cues + Jane Perry voiceover.
# SFX instruments reused from ../film.
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); FILM = os.path.join(HERE, '..', 'film')
a = open(os.path.join(FILM, 'audio.py')).read(); a = a[:a.index("exec(open(os.path.join(ROOT, 'score_v3.py'))")]
a = a.replace("ROOT = os.path.dirname(os.path.abspath(__file__))", "ROOT = HERE")
exec(a)
b = open(os.path.join(FILM, 'score_v3.py')).read(); exec(b[:b.index('def score_v3():')])
CUTS = [C['card1'], C['card2'], C['card3'], C['card4'], C['white']]
# music: the approved draft A bed (music/track.py)
def rv2(p):
    w = wave.open(p); x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768; return x.reshape(-1, w.getnchannels())
m = rv2(os.path.join(HERE, 'music', 'music.wav')); music[:min(N, len(m))] += m[:N]
# sound design — every effect has a visible source, kept clearly audible over the music
for k in range(14): tickp(.05 + k * .03, .12 * (1 - k / 16), 3800 + 450 * (k % 4), (-1) ** k * .45)       # pixel blocks flicker on
mask(C['icon'] + .1, .2); whoosh(C['icon'] - .05, .4, .3, 600, 5000, -.3, .3, .5)                    # icon appears
for k in range(16): tick(C['roll'] + k * .05, .1 + .004 * k, .15)                                     # number rolls
t_ = tv(C['hot'] - C['roll']); add(sfx, C['roll'], np.sin(2 * np.pi * np.cumsum(260 * 4 ** (t_ / t_[-1])) / SR) * (t_ / t_[-1]) ** 2 * .5, .12)   # heat rising
for k, w_ in enumerate(['Your', 'content', 'needs', 'more', 'heat.']): mask(C['cap'] + k * .12, .1, -.2 + .1 * k)
riser(C['build1'] - .4, C['card1'], .09)
for c in CUTS:
    hit(c, .3); whoosh(c - .14, .26, .26, 400, 9000, -.7, .7, .7); crash(c, .05)
for st, *_ in C['SHOTS']:
    if all(abs(st - c) > .02 for c in CUTS): whoosh(st - .08, .18, .16, 1200, 9000, .5, -.5, .6); click(st, .14, 3600, .2)
thump(C['title1'], .2, 160, 60, .08); tone(C['title1'] + .02, 1318.5, .06)                             # "Impact" lands
for c in CUTS[:4]:
    for i in range(5): tone(c + .1 + i * .045, 1568 * 1.06 ** i, .035, -.4 + .2 * i, .04)              # stars pop
for a0, c in [(C['build2'] - .3, C['card2']), (C['build3'] - .2, C['card3']), (C['card4'] - .45, C['card4']), (C['build5'] - .2, C['white'])]: riser(a0, c, .07)
scrub(C['white'] + .03, C['stop'] - .02, .08); click(C['stop'], .24, 2600); tone(C['stop'] + .02, 1760, .06)
thump(C['slam'], .32, 150, 55, .1); thump(C['slam'] + .07, .24, 150, 55, .1)
whoosh(C['purpose'] - .05, .3, .12, 1500, 8000, -.5, .5, .5); whoosh(C['purpose'] + .15, .35, .1, 2000, 9000, -.4, .4, .5)   # marker swipe
whoosh(C['lock'] - .2, .35, .14, 3000, 600, 0, 0, .4); mask(C['logo'] + .05, .1); thump(C['logo'] + .1, .16, 140, 60, .08)
for i in range(6): tick(C['studio'] + i * .04, .04, -.3 + .12 * i)                                     # STUDIO tracks in
whoosh(C['rule'], .3, .08, 2000, 7000, -.6, .6, .5)
whoosh(C['dm'] - .05, .3, .1, 500, 3000, 0, 0, .6); mask(C['dm'] + .1, .08)
for k in range(6): click(C['type'] + k * .075, .16, 3400 + 200 * k, .1)                                # S-A-M-P-L-E
click(C['send'] - .02, .2, 2400); whoosh(C['send'], .3, .16, 800, 9000, -.2, .7, .4); tone(C['send'] + .06, 1760, .07); tone(C['send'] + .12, 2637, .05)
# voice (Jane Perry): natural speed; only the pause inside line 6 is shortened
def rv(p):
    w = wave.open(p); return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
VOD = os.path.join(HERE, 'vo')
def vline(i, t0, cut=None):
    x = rv(os.path.join(VOD, f'r{i}.wav')); x = hp(x, 90, 2); x = x + .22 * bp(x, 2500, 6500)
    if cut: a0, a1 = int(cut[0] * SR), int(cut[1] * SR); x = np.concatenate([x[:a0], x[a1:]])
    on = np.where(np.abs(x) > .015)[0][0]; x = x[on - int(.01 * SR):]; x[:480] *= np.linspace(0, 1, 480); x[-2400:] *= np.linspace(1, 0, 2400)
    add(vox, t0 - .01, x, 1.0)
vline(1, 0.75); vline(2, 2.70); vline(3, 4.64); vline(4, 6.38); vline(5, 8.25); vline(6, 10.25, (1.03, 1.18)); vline(7, 12.95)
vn = .32 / (np.percentile(np.abs(vox[np.abs(vox).max(1) > 1e-3]).max(1), 99) + 1e-9)
envv = np.abs(vox).max(1); k = int(.03 * SR); envv = np.sqrt(np.convolve(envv ** 2, np.ones(k) / k, 'same'))
act = np.clip(envv / .02, 0, 1); gg = np.zeros_like(act); s_ = 0; ac, rc = np.exp(-1 / (.02 * SR)), np.exp(-1 / (.25 * SR))
for i in range(len(act)):
    v = act[i]; c = ac if v > s_ else rc; s_ = c * s_ + (1 - c) * v; gg[i] = s_
mix = .38 * music * (1 - .4 * gg)[:, None] + .9 * sfx * (1 - .2 * gg)[:, None] + vox * vn
fo = int(.3 * SR); mix[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 1.5
mix = np.tanh(mix * 1.1) / 1.1
os.makedirs(os.path.join(HERE, 'build'), exist_ok=True)
y = np.clip(mix, -1, 1); w = wave.open(os.path.join(HERE, 'build', 'mix_raw.wav'), 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((y * 32767).astype(np.int16).tobytes()); w.close()
# overlap check for the voice lines
print('ok peak', float(np.abs(mix).max()))
if '--report' in sys.argv:
    db = lambda x: 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9)
    for a0 in np.arange(0, 15, 1.25):
        i, j = int(a0 * SR), int((a0 + 1.25) * SR)
        print(f"{a0:5.2f}  music {db(.38*music[i:j]):6.1f}  sfx {db(.9*sfx[i:j]):6.1f}  voice {db(vox[i:j]*vn):6.1f}")
