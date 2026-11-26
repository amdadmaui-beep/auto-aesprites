# Perplexity spot sound: original score (112 BPM, C major), synthesized UI sound design, Fish VO placed on the
# reference timeline (vo/vo_placed.wav). Writes build/{music,sfx,vo,mix_raw}.wav
import json, os
import numpy as np, soundfile as sf
from scipy import signal
from scipy.signal import fftconvolve, resample_poly
HERE = os.path.dirname(os.path.abspath(__file__)); SR = 48000
WORDS = json.load(open(os.path.join(HERE, '..', 'vo', 'words_placed.json')))
def w(word, k=0):
    m = [x for x in WORDS if x[0].lower().strip('.,?!') == word]; return m[min(k, len(m) - 1)][1]
DUR = 44.5; N = int(DUR * SR); B = 60 / 112; DROP = w("that's"); G0 = DROP - 32 * B; rng = np.random.default_rng(5)
def tv(d): return np.arange(int(d * SR)) / SR
def lp(x, f, o=2): b, a = signal.butter(o, min(f, SR / 2 - 200) / (SR / 2), 'low'); return signal.lfilter(b, a, x, axis=0)
def hp(x, f, o=2): b, a = signal.butter(o, f / (SR / 2), 'high'); return signal.lfilter(b, a, x, axis=0)
def bp(x, f1, f2, o=2): b, a = signal.butter(o, [f1 / (SR / 2), min(f2, SR / 2 - 200) / (SR / 2)], 'band'); return signal.lfilter(b, a, x, axis=0)
def sine(f, t): return np.sin(2 * np.pi * f * t)
def sweep(f, t): return np.sin(2 * np.pi * np.cumsum(f) / SR)
def att(t, a=.003): return np.minimum(1, t / a)
def m2f(m): return 440 * 2 ** ((m - 69) / 12)
def add(buf, t0, x, g=1., pan=0.):
    if x.ndim == 1: x = np.stack([x * np.cos((pan + 1) * np.pi / 4), x * np.sin((pan + 1) * np.pi / 4)], 1) * 1.414
    i = int(round(t0 * SR))
    if i < 0: x = x[-i:]; i = 0
    j = min(len(buf), i + len(x))
    if j > i: buf[i:j] += (x[:j - i] * g).astype(np.float32)
def room(x, dec=.6, length=2.5, seed=3, lpf=6000):
    r = np.random.default_rng(seed); t = tv(length); out = []
    for c in (0, 1):
        ir = lp(r.standard_normal(len(t)) * np.exp(-t / dec), lpf); ir /= np.sqrt((ir ** 2).sum()); out.append(fftconvolve(x[:, c], ir)[:len(x)])
    return np.stack(out, 1).astype(np.float32)
def curve(pts): return np.interp(np.arange(N) / SR, [p[0] for p in pts], [p[1] for p in pts]).astype(np.float32)


st = {k: np.zeros((N, 2), np.float32) for k in ['kick', 'snare', 'hat', 'shk', 'bass', 'pluck', 'keys', 'pad', 'tick']}
def kick():
    t = tv(.45); return (sweep(45 + 120 * np.exp(-t / .028), t) * np.exp(-t / .22) + .25 * lp(rng.standard_normal(len(t)), 2500) * np.exp(-t / .004)) * att(t, .001)
def snare():
    t = tv(.4); n = bp(rng.standard_normal(len(t)), 1200, 7000) * np.exp(-t / .07); b = sine(190, t) * np.exp(-t / .05); return (n * .9 + .5 * b) * att(t, .001)
def hat(d=.05): t = tv(d); return hp(rng.standard_normal(len(t)), 8000) * np.exp(-t / .016)
def shk(): t = tv(.08); return hp(rng.standard_normal(len(t)), 5000) * np.sin(np.pi * np.minimum(1, t / .08)) ** 2
def bass(f, d): t = tv(d); x = np.tanh(1.8 * (sine(f, t) + .25 * sine(2 * f, t))) * np.exp(-t / .6) * att(t, .005); return lp(x, 600)
def pluck(f):
    t = tv(.5); x = (sine(f, t) + .45 * sine(2 * f, t) * np.exp(-t / .05) + .15 * sine(3 * f, t) * np.exp(-t / .02)) * np.exp(-t / .14) * att(t, .002); return lp(x, 4500)
def ep(f, d=1.8): t = tv(d); return (sine(f, t) + .3 * sine(2 * f, t) * np.exp(-t / .25) + .1 * sine(3.01 * f, t) * np.exp(-t / .1)) * np.exp(-t / 1.0) * att(t, .005)
def pad(notes, d):
    t = tv(d); x = sum(sum(np.sin(2 * np.pi * m2f(n) * (1 + dt) * t + rng.uniform(0, 6)) for dt in (-.005, 0, .005)) for n in notes)
    return lp(x * np.minimum(1, t / .5) * np.minimum(1, np.maximum(0, d - t) / .5), 2200) / 8
def tick(f=2600): t = tv(.04); return (sine(f, t) * np.exp(-t / .006) + .3 * bp(rng.standard_normal(len(t)), 2000, 6000) * np.exp(-t / .003))

PROG = [[48, 52, 55, 59], [43, 47, 50, 55], [45, 48, 52, 55], [41, 45, 48, 52]]   # Cmaj7  G  Am  Fmaj7
BASSN = [36, 31, 33, 29]; ARP = [0, 2, 1, 3, 2, 1, 3, 2]
bar = 4 * B
for b_ in range(int((DUR - G0) / bar) + 1):
    t0 = G0 + b_ * bar; ch = PROG[b_ % 4]
    add(st['pad'], t0, pad([n + 12 for n in ch[:3]], bar + .6), .55)
    add(st['kick'], t0, kick(), .8); add(st['kick'], t0 + 2.5 * B, kick(), .4); add(st['kick'], t0 + 2 * B, kick(), .55)
    add(st['snare'], t0 + B, snare(), .26); add(st['snare'], t0 + 3 * B, snare(), .3)
    for s in range(8): add(st['hat'], t0 + s * B / 2 + (.014 if s % 2 else 0), hat(), .1 if s % 2 else .05, .35)
    for s in range(16): add(st['shk'], t0 + s * B / 4, shk(), .03 + .02 * (s % 4 == 2), -.3)
    for s in range(8): add(st['pluck'], t0 + s * B / 2, pluck(m2f(ch[ARP[s] % len(ch)] + 24)), .15, .45 * np.sin(1.3 * s))
    for k, n in enumerate(ch): add(st['keys'], t0 + k * .008, ep(m2f(n + 12)), .07, rng.uniform(-.3, .3))
    add(st['bass'], t0, bass(m2f(BASSN[b_ % 4]), 1.0), .38); add(st['bass'], t0 + 2.5 * B, bass(m2f(BASSN[b_ % 4] + 12), .4), .2)
    for s in range(4): add(st['tick'], t0 + s * B, tick(2600 if s % 2 else 3100), .07)
SIMP = w('simple') - .02; BRK = 38.45; END = w('perplexity', 4) - .05
Gn = {
 'pad':   curve([(0, .9), (SIMP, .9), (SIMP + .05, .2), (DROP, 1), (BRK, 1), (BRK + .1, 1.2), (END, 1.2), (END + .05, 0), (DUR, 0)]),
 'pluck': curve([(0, 0), (2.6, 0), (2.8, .7), (SIMP, .7), (SIMP + .02, 0), (DROP - .01, 0), (DROP, 1), (BRK, 1), (BRK + .05, .6), (END, .6), (END + .02, 0), (DUR, 0)]),
 'tick':  curve([(0, 0), (2.6, 0), (2.8, .8), (9.6, .8), (9.8, 1), (SIMP, 1), (SIMP + .02, 0), (DROP, 0), (DUR, 0)]),
 'shk':   curve([(0, 0), (9.6, 0), (9.8, .7), (SIMP, .7), (SIMP + .02, 0), (DROP - .01, 0), (DROP, 1), (BRK, 1), (BRK + .05, 0), (DUR, 0)]),
 'kick':  curve([(0, 0), (DROP - .01, 0), (DROP, 1), (BRK, 1), (BRK + .05, 0), (DUR, 0)]),
 'snare': curve([(0, 0), (DROP - .01, 0), (DROP, 1), (BRK, 1), (BRK + .05, 0), (DUR, 0)]),
 'hat':   curve([(0, 0), (9.6, 0), (9.8, .5), (SIMP, .5), (SIMP + .02, 0), (DROP - .01, 0), (DROP, 1), (BRK, 1), (BRK + .05, 0), (DUR, 0)]),
 'bass':  curve([(0, 0), (DROP - .01, 0), (DROP, 1), (BRK, 1), (BRK + .05, .4), (END, .4), (END + .05, 0), (DUR, 0)]),
 'keys':  curve([(0, 0), (DROP - .01, 0), (DROP, .9), (BRK, .9), (BRK + .05, .7), (END, .7), (END + .05, 0), (DUR, 0)]),
}
music = sum(st[k] * Gn[k][:, None] for k in Gn)
i0 = int(0); i1 = int(2.75 * SR); music[i0:i1] = lp(music[i0:i1], 1800)            # the intro sits under a low-pass
for k, n in enumerate([36, 48, 55, 60, 64, 67, 71]): add(music, END + k * .012, ep(m2f(n), 5.0) * np.exp(-tv(5.0) / 2.2), .2 if n > 40 else .45)
add(music, END, pad([60, 64, 67, 71], DUR - END), .9)
for t0, n in [(END + .45, 76), (w('start') - .05, 79), (w('today') - .05, 84)]:
    t = tv(2.5); add(music, t0, (sine(m2f(n), t) + .3 * sine(m2f(n) * 2.76, t) * np.exp(-t / .2)) * np.exp(-t / .8) * att(t), .07)
music = music + .22 * room(music, .9, 3.0)
music *= curve([(0, 0), (.25, 1), (43.4, 1), (DUR, 0)])[:, None]

sfx = np.zeros((N, 2), np.float32)
def pop(t0, g=.3, f=900, pan=0.):
    t = tv(.12); x = sweep(f * (1 + 1.2 * np.exp(-t / .012)), t) * np.exp(-t / .03) * att(t, .001); add(sfx, t0, lp(x, 6000), g, pan)
def click(t0, g=.35, pan=0.):
    t = tv(.05); x = bp(rng.standard_normal(len(t)), 1500, 7000) * np.exp(-t / .004) + .5 * sine(2400, t) * np.exp(-t / .006); add(sfx, t0, x, g, pan)
def key(t0, g=.13, pan=0.):
    t = tv(.06); x = bp(rng.standard_normal(len(t)), 2000, 8000) * np.exp(-t / .006) + .4 * sine(rng.uniform(300, 420), t) * np.exp(-t / .01)
    add(sfx, t0, x, g * rng.uniform(.7, 1.1), pan + rng.uniform(-.15, .15))
def whoosh(t0, d=.5, g=.3, f0=300, f1=4000, p0=-.5, p1=.5):
    t = tv(d); x = rng.standard_normal(len(t)); y = np.zeros_like(x); seg = 512
    for i in range(0, len(x), seg):
        fc = f0 * (f1 / f0) ** (i / len(x)); y[i:i + seg] = bp(x[max(0, i - 2048):i + seg], fc / 1.8, min(fc * 1.8, 16000))[-len(x[i:i + seg]):]
    e = np.sin(np.pi * t / d) ** 2; pn = np.linspace(p0, p1, len(t))
    add(sfx, t0 - d / 2, np.stack([y * e * np.cos((pn + 1) * np.pi / 4), y * e * np.sin((pn + 1) * np.pi / 4)], 1) * 1.6, g)
def chime(t0, g=.2, n=84, pan=0.):
    t = tv(1.4); f = m2f(n); x = (sine(f, t) + .4 * sine(2 * f, t) * np.exp(-t / .3) + .2 * sine(3.01 * f, t) * np.exp(-t / .08)) * np.exp(-t / .45) * att(t, .002); add(sfx, t0, x, g, pan)
def thud(t0, g=.5, f0=90, f1=38):
    t = tv(.6); add(sfx, t0, sweep(f1 + (f0 - f1) * np.exp(-t / .05), t) * np.exp(-t / .22) * att(t, .002), g)
def riser(t0, d=.8, g=.12):
    t = tv(d); x = bp(rng.standard_normal(len(t)), 800, 9000) * (t / d) ** 2.5; add(sfx, t0 - d, x, g)


# intro: phone rises, objects burst, dive into the words
whoosh(.35, .9, .25, 250, 4000, -.3, .3)
for i in range(14): pop(.6 + i * .04, .1, 700 + 60 * (i % 5), np.sin(i * 1.7) * .7)
riser(2.5, .7, .1); whoosh(2.6, .5, .3, 5000, 400, .4, -.4)
# words land softly; icons scatter; ring of noise; simple
for word in ['every', 'day', "there's", 'something', "you've", 'never', 'done', 'before']: pop(w(word) - .02, .07, 1300, .1)
whoosh(5.6, .6, .2, 600, 6000, -.6, .6)
for i in range(16): pop(5.65 + i * .02, .06, 900 + 40 * i, np.sin(i) * .8)
chime(w('new') + .02, .1, 84); whoosh(9.4, .5, .3, 5000, 300, 0, 0)
for i in range(20): pop(10.05 + i * .05, .06, 800 + 30 * (i % 7), np.sin(i * 2.1) * .8)
riser(SIMP, 1.2, .12); thud(SIMP, .45, 90, 40); whoosh(13.75, .45, .25, 300, 5000, 0, 0)
# drop: the dot, the mark draws, the word slides out
pop(13.98, .3, 900); chime(14.45, .16, 79); chime(14.85, .12, 84); whoosh(14.9, .7, .18, 600, 3000, -.4, .4)
whoosh(16.4, .9, .28, 200, 3500, 0, 0); thud(16.4, .3, 80, 40)
whoosh(19.9, .8, .3, 400, 7000, 0, 0)
Q = 'How do I make pizza at home?'; tq0, tq1 = w('want', 1), w('pizza') + .45
for i, ch in enumerate(Q):
    if ch != ' ': key(tq0 + (tq1 - tq0) * i / len(Q), .14)
whoosh(21.65, .7, .1, 2500, 900, .3, .5); click(22.12, .5, .3); whoosh(22.45, .55, .32, 5000, 300, 0, 0)
# pizza: sources, ticks, toppings
for i in range(4): pop(w('perplexity', 1) + i * .12, .12, 1100 + 100 * i, .3)
for i in range(5): click(w('ingredients') + .1 + i * .13, .2, .3)
for i in range(4): click(w('all') + i * .12, .2, .3)
for i in range(11): pop(w('process') + .3 + i * .05, .08, 700 + 50 * i, -.4)
chime(w('all') + .5, .14, 86)
whoosh(26.9, .5, .3, 5000, 300, 0, 0)
for i, k in enumerate([0, 1, 2]): pop(w('new', 1) + .05 + i * .4, .2, [900, 1100, 1300][i], 0)
whoosh(31.6, .5, .3, 5000, 300, 0, 0); whoosh(31.95, .9, .25, 200, 4000, 0, 0)
pop(32.2, .2, 1000, .2)
for i in range(4): pop(w('every', 1) - .1 + i * .16, .1, 1200 + 80 * i, .2)
for i in range(4): click(w('simply') + i * .3, .22, .2)
for i in range(8): pop(w('perplexity', 3) + .15 + i * .09, .1, 800 + 70 * i, np.sin(i * 1.3) * .8)
whoosh(38.25, .45, .3, 5000, 300, 0, 0)
for word, k, s in [('learn', 0, 'Learn it'), ('do', 1, 'Do it'), ('make', 1, 'Make it done')]:
    t0 = w(word, k); d = .55 if s.startswith('Make') else .3
    for i in range(len(s)): key(t0 + d * i / len(s), .12)
whoosh(41.3, .6, .3, 300, 5000, 0, 0); thud(END, .45, 90, 36); chime(END + .2, .14, 79)
sfx = sfx + .16 * room(sfx, .35, 1.5, 9)

x, sr = sf.read(os.path.join(HERE, '..', 'vo', 'vo_placed.wav'), dtype='float32')
if x.ndim > 1: x = x.mean(1)
if sr != SR: x = resample_poly(x, SR, sr).astype(np.float32)
x = hp(x, 90); env = np.sqrt(np.convolve(x ** 2, np.ones(480) / 480, 'same')) + 1e-6; x = x * np.minimum(1, (env / .08) ** -.35)
vo = np.zeros((N, 2), np.float32); add(vo, 0, x, 1.0); vo = vo + .05 * room(vo, .22, .9, 4, 5000)
m = np.abs(vo).max(1); a_, r_ = np.exp(-1 / (.01 * SR)), np.exp(-1 / (.25 * SR)); e = np.empty_like(m); c = 0.
for k in range(len(m)): v = m[k]; c = a_ * c + (1 - a_) * v if v > c else r_ * c + (1 - r_) * v; e[k] = c
duck = 1 - .5 * np.clip(e / (np.percentile(e[e > 1e-4], 85) + 1e-9), 0, 1)
def rms(x, thr=None): x = x if thr is None else x[np.abs(x).max(1) > thr]; return float(np.sqrt(np.mean(x ** 2)) + 1e-9)
music *= 10 ** (-20 / 20) / rms(music[int(DROP * SR):int(BRK * SR)]); music *= duck[:, None]
sfx *= 10 ** (-24 / 20) / rms(sfx, 1e-3)
vo *= 10 ** (-15 / 20) / rms(vo, .01)
os.makedirs(os.path.join(HERE, 'build'), exist_ok=True)
for n, y in [('music', music), ('sfx', sfx), ('vo', vo), ('mix_raw', music + sfx + vo)]: sf.write(os.path.join(HERE, 'build', n + '.wav'), y.astype(np.float32), SR, subtype='FLOAT')
print('ok', round(float(np.abs(music + sfx + vo).max()), 2))
