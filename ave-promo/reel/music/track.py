# "More heat" bed, music only — 96 BPM, F minor, 15s (6 bars). Evolves every bar: no looped phrase.
import numpy as np, wave
from scipy import signal
from scipy.signal import fftconvolve
SR = 48000; DUR = 15.0; N = int(DUR * SR); rng = np.random.default_rng(3)
BPM = 96; BEAT = 60 / BPM; BAR = 4 * BEAT; S16 = BEAT / 4
L = np.zeros((N, 2), np.float32); VERB = np.zeros((N, 2), np.float32); DLY = np.zeros((N, 2), np.float32)
def tv(d): return np.arange(int(d * SR)) / SR
def nf(n):
    m = {'C':0,'C#':1,'Db':1,'D':2,'Eb':3,'E':4,'F':5,'Gb':6,'G':7,'Ab':8,'A':9,'Bb':10,'B':11}
    return 440 * 2 ** ((12 * (int(n[-1]) + 1) + m[n[:-1]] - 69) / 12)
def lp(x, f, o=2): b, a = signal.butter(o, min(f, SR/2-100) / (SR/2), 'low'); return signal.lfilter(b, a, x)
def hp(x, f, o=2): b, a = signal.butter(o, f / (SR/2), 'high'); return signal.lfilter(b, a, x)
def bp(x, a_, b_, o=2): b, a = signal.butter(o, [a_ / (SR/2), b_ / (SR/2)], 'band'); return signal.lfilter(b, a, x)
def add(t0, x, g=1., pan=0., verb=0., dly=0.):
    if x.ndim == 1: x = np.stack([x * np.cos((pan+1)*np.pi/4), x * np.sin((pan+1)*np.pi/4)], 1) * 1.414
    i = int(round(t0 * SR)); j = min(N, i + len(x))
    if j <= i: return
    L[i:j] += x[:j-i] * g; VERB[i:j] += x[:j-i] * g * verb; DLY[i:j] += x[:j-i] * g * dly
noise = lambda d: rng.standard_normal(int(d * SR))
# ---- instruments
def epiano(t0, notes, d, g=.08, bright=1., pan=0.):          # FM electric piano: warm tine + bark
    t = tv(d + 1.2); x = np.zeros_like(t)
    for k, n in enumerate(notes):
        f = nf(n); det = 1 + .0015 * (k - len(notes) / 2)
        x += np.sin(2*np.pi*f*det*t + (1.8*bright) * np.exp(-t/.18) * np.sin(2*np.pi*f*det*t)) * np.exp(-t/1.6)
        x += .18 * np.sin(2*np.pi*f*7*t) * np.exp(-t/.03)
    x *= np.minimum(1, t/.004) * np.clip((d + .5 - t) / .5, 0, 1)
    trem = 1 + .12 * np.sin(2*np.pi*5.2*t)
    add(t0, np.stack([x*trem, x*(2-trem)], 1) / len(notes) * .9, g, 0, .35, .12)
def arp(t0, n, g=.05, pan=0., dec=.22, cut=4000):
    f = nf(n); t = tv(.9); x = signal.sawtooth(2*np.pi*f*t) * .5 + signal.square(2*np.pi*f*1.004*t) * .3
    x = lp(x * np.exp(-t/dec) * np.minimum(1, t/.002), cut); add(t0, x, g, pan, .2, .45)
def sub(t0, d, n, g=.3, slide=0.):
    f = nf(n); t = tv(d + .05); ff = f * 2 ** (slide * np.exp(-t/.05) / 12)
    x = np.sin(2*np.pi*np.cumsum(ff)/SR); x = np.tanh(1.8*x) + .25*np.sin(2*np.pi*np.cumsum(2*ff)/SR)
    x *= np.minimum(1, t/.004) * np.clip((d + .03 - t) / .04, 0, 1); add(t0, lp(x, 300), g)
def kick(t0, g=.5):
    t = tv(.5); f = 45 + 110*np.exp(-t/.025); x = np.tanh(2*np.sin(2*np.pi*np.cumsum(f)/SR)) * np.exp(-t/.25)
    x += .4 * bp(noise(.5), 2500, 9000) * np.exp(-t/.003); add(t0, x, g)
def snare(t0, g=.16, verb=.4):
    t = tv(.45); x = .6*bp(noise(.45), 1200, 7000) * np.exp(-t/.09) + .4*np.sin(2*np.pi*200*t)*np.exp(-t/.04)
    for d in (0, .01, .02): x[:int(.04*SR)] += .3 * np.roll(bp(noise(.45), 900, 5000), int(d*SR))[:int(.04*SR)] * np.exp(-t[:int(.04*SR)]/.01)
    add(t0, x, g, -.05, verb)
def hat(t0, g=.025, pan=.3, op=False):
    t = tv(.4); add(t0, hp(noise(.4), 8000) * np.exp(-t/(.13 if op else .02)), g, pan)
def shaker(t0, g=.014): t = tv(.08); add(t0, bp(noise(.08), 5000, 12000) * np.sin(np.pi*np.minimum(1, t/.07))**2, g, -.35)
def pad(t0, d, notes, g=.04, cut=1200):
    t = tv(d + 1.0); Lc = np.zeros_like(t); Rc = np.zeros_like(t)
    for n in notes:
        f = nf(n); Lc += signal.sawtooth(2*np.pi*f*.997*t + rng.random()*6); Rc += signal.sawtooth(2*np.pi*f*1.003*t + rng.random()*6)
    e = np.minimum(1, t/.6) * np.clip((d + 1.0 - t) / 1.0, 0, 1)
    add(t0, np.stack([lp(Lc, cut), lp(Rc, cut)], 1) * e[:, None] / len(notes), g, 0, .4)
def riser(t0, t1, g=.05):
    d = t1 - t0; t = tv(d); z = noise(d); y = np.zeros_like(t); seg = 512
    for i in range(0, len(t), seg):
        fc = 300 * 30 ** (i / len(t)); y[i:i+seg] = bp(z[max(0, i-1024):i+seg], fc*.7, min(fc*1.5, 20000))[-len(z[i:i+seg]):]
    add(t0, y * (t/d) ** 2.5, g, 0, .3)
def impact(t0, g=.35):
    t = tv(2.0); f = 38 * (1 + 1.2*np.exp(-t/.06)); x = np.tanh(2*np.sin(2*np.pi*np.cumsum(f)/SR)) * np.exp(-t/.6)
    x += .4 * lp(noise(2.0), 1500) * np.exp(-t/.05); add(t0, x, g, 0, .5)
def chop(t0, n, g=.05, pan=0.):                                # vowel-ish "vocal chop" from a formant-filtered saw
    f = nf(n); t = tv(.32); x = signal.sawtooth(2*np.pi*f*t*(1 + .01*np.sin(2*np.pi*6*t)))
    y = bp(x, 650, 1100) + .6*bp(x, 1700, 2600); y *= np.sin(np.pi*np.minimum(1, t/.3))**1.2; add(t0, y, g, pan, .5, .4)
# ---- harmony (two chords per bar)
CH = [(['F3','Ab3','C4','Eb4','G4'], 'F1'), (['Db3','F3','Ab3','C4'], 'Db2'), (['Ab2','C3','Eb3','G3','Bb3'], 'Ab1'), (['Eb3','G3','Bb3','C4'], 'Eb2'),
      (['Bb2','Db3','F3','Ab3','C4'], 'Bb1'), (['C3','E3','G3','Bb3','Db4'], 'C2')]
def chord(i): return CH[i % len(CH)]
SCALE = ['F4','G4','Ab4','Bb4','C5','Db5','Eb5','F5','G5','Ab5','C6']
ARPS = [[0,2,4,7,4,2], [4,7,9,7,4,2,4,6], [0,4,2,6,4,8,6,9], [7,6,4,2,4,6,7,9], [9,7,6,4,6,7,4,2], [4,2,0,2,4,7,9,10]]
# bar 1 · intro (0–2.5): filtered keys, sparse arp, riser into the 99 hit
epiano(0.0, chord(0)[0], BAR/2, .07, .6); epiano(BAR/2, chord(1)[0], BAR/2, .07, .7)
pad(0.0, BAR, ['F3','C4','Eb4'], .03, 700)
for k, s in enumerate([0, 3, 6, 8, 11, 14]): arp(s*S16*2 * .5 + .3, SCALE[ARPS[0][k % 6]], .035, -.4 + .16*k, .25, 2200 + 300*k)
sub(BAR/2, BAR/2, 'Db2', .12)
riser(1.2, BAR, .06)
for k in range(8): hat(BAR - 8*S16/2 + k*S16/2, .012 + .003*k, .2)
# bars 2–4 · groove (2.5–10): new chord pair, new arp shape and new bass rhythm every bar
BASS = [[(0,3),(3,1),(6,2),(10,2),(12,2),(14,1)], [(0,2),(3,2),(7,1),(8,3),(11,2),(14,2)], [(0,3),(4,1),(6,2),(9,1),(10,2),(13,3)]]
for bi in range(3):
    b0 = BAR * (1 + bi); c1, c2 = chord(2*bi + 2), chord(2*bi + 3)
    impact(b0, .3 if bi == 0 else .12)
    for half, (notes, root) in enumerate([c1, c2]):
        h0 = b0 + half * BAR / 2
        epiano(h0, notes, BAR/2 - .05, .07, .9 + .1*bi, 0)
        for s, l in BASS[bi]:
            if s < 8: sub(h0 + s*S16, l*S16*.92, root, .26, 3 if s == 0 else 0)
            else: pass
        for s, l in BASS[bi]:
            if s >= 8 and half == 0: pass
    for s in range(16):
        t = b0 + s*S16 + (.012 if s % 2 else 0)
        if s in (0, 7, 10) or (bi == 2 and s == 14): kick(b0 + s*S16, .45 if s == 0 else .36)
        if s in (4, 12): snare(b0 + s*S16, .15)
        if s in (6, 15) and bi > 0: snare(t, .035, .1)
        hat(t, .022 if s % 4 == 2 else .013, .3, op=(s == 14))
        if s % 2: shaker(t)
    pat = ARPS[1 + bi]
    for k in range(16 if bi > 0 else 8):
        st = b0 + k * (S16 if bi > 0 else 2*S16)
        arp(st, SCALE[pat[k % len(pat)]], .03, -.5 + .0625*k, .18, 3000 + 400*bi)
    for k, n in enumerate([['C5','Eb5','F5'], ['Ab4','C5','Eb5','G5'], ['F5','Eb5','C5','Ab4','G4']][bi]):
        chop(b0 + BAR/2 + k*BEAT*.5, n, .045, .3 - .2*k)
    for k in range(4): snare(b0 + BAR - 4*S16 + k*S16, .03 + .02*k, .2)         # fill into the next bar
riser(BAR*4 - 1.0, BAR*4, .07)
# bar 5 · breakdown (10–12.5): keys + chops, no drums, a held breath before the lockup
impact(BAR*4, .22); epiano(BAR*4, chord(0)[0], BAR/2, .08, 1.0); epiano(BAR*4 + BAR/2, ['Db3','F3','Ab3','C4','Eb4'], BAR/2, .08, 1.0)
pad(BAR*4, BAR, ['F3','Ab3','C4','G4'], .045, 1600)
for k, n in enumerate(['C5','Ab4','G4','F4','Eb4','F4']): chop(BAR*4 + .3 + k*BEAT*.66, n, .04, -.3 + .12*k)
sub(BAR*4, BAR*.45, 'F1', .2); sub(BAR*4 + BAR/2, BAR*.45, 'Db2', .18)
riser(BAR*5 - .8, BAR*5, .05)
# bar 6 · resolve (12.5–15): groove returns light, ends on an open chord
b0 = BAR*5; impact(b0, .2)
epiano(b0, ['Ab2','C3','Eb3','G3','C4'], BAR/2, .07); epiano(b0 + BAR/2, ['Db3','F3','Ab3','C4','Eb4','G4'], BAR/2 + 1, .08)
sub(b0, BAR*.45, 'Ab1', .22, 3); sub(b0 + BAR/2, BAR*.5, 'Db2', .22)
for s in range(16):
    t = b0 + s*S16
    if s in (0, 10): kick(t, .38)
    if s == 4 or s == 12: snare(t, .12)
    if s < 12: hat(t + (.012 if s % 2 else 0), .014, .3)
for k, n in enumerate(['C5','Eb5','G5','C6']): arp(b0 + BAR/2 + k*S16*2, n, .04, -.3 + .2*k, .6, 5000)
# mix: room + ping-pong delay, glue
ir_t = tv(1.6); ir = rng.standard_normal(len(ir_t)) * np.exp(-ir_t/.45); ir /= np.sqrt((ir**2).sum())
for c in (0, 1): L[:, c] += fftconvolve(VERB[:, c], ir * (1 if c else .96), 'full')[:N].astype(np.float32) * .35
d1 = int(BEAT*.75*SR); src = lp(DLY.mean(1), 4500)
for k in range(1, 6):
    d = d1*k
    if d < N: L[d:, k % 2] += src[:N-d] * (.42**k)
fo = int(.6*SR); L[-fo:] *= np.linspace(1, 0, fo)[:, None]**1.5
L = np.tanh(L * 1.2) / 1.2
y = np.clip(L, -1, 1); w = wave.open('music.wav', 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((y*32767).astype(np.int16).tobytes()); w.close()
print('ok', float(np.abs(L).max()))
