# V3 sound: original score (160 BPM, half-time feel, D minor / F major), synthesized UI sound design,
# and the single Fish Audio VO take. Everything is timed from cues.js. Writes build/{music,sfx,vo,mix_raw}.wav
import json, os, re
import numpy as np, soundfile as sf
from scipy import signal
from scipy.signal import fftconvolve, resample_poly

HERE = os.path.dirname(os.path.abspath(__file__)); SR = 48000
src = re.sub(r'//[^\n]*', '', open(os.path.join(HERE, 'cues.js')).read())
C = json.loads(src[src.index('{'):src.rindex('}') + 1]); W = C['w']
DUR = C['dur']; N = int(DUR * SR); B = 60 / C['bpm']; G0 = C['grid0']; rng = np.random.default_rng(11)
beat = lambda k: G0 + k * B
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

# ================================================================ score
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
PROG = [[50, 53, 57, 60], [46, 50, 53, 57], [53, 57, 60, 64], [48, 52, 55, 60]]   # Dm7  Bbmaj7  F  C
BASSN = [38, 34, 41, 36]; ARP = [0, 2, 1, 3, 2, 1, 3, 2]
bar = 4 * B
for b_ in range(int(DUR / bar) + 2):
    t0 = G0 + b_ * bar; ch = PROG[(b_ // 2) % 4]                     # one chord per two bars
    if b_ % 2 == 0: add(st['pad'], t0, pad([n + 12 for n in ch[:3]], 2 * bar + .6), .55)
    add(st['kick'], t0, kick(), .8); add(st['kick'], t0 + 2.5 * B, kick(), .45)
    add(st['snare'], t0 + 2 * B, snare(), .32)
    for s in range(8): add(st['hat'], t0 + s * B / 2 + (.012 if s % 2 else 0), hat(), .10 if s % 2 else .06, .35)
    for s in range(16): add(st['shk'], t0 + s * B / 4, shk(), .035 + .02 * (s % 4 == 2), -.3)
    for s in range(8): add(st['pluck'], t0 + s * B / 2, pluck(m2f(ch[ARP[s] % len(ch)] + 24)), .15, .45 * np.sin(1.3 * s))
    for k, n in enumerate(ch): add(st['keys'], t0 + k * .006, ep(m2f(n + 12)), .07, rng.uniform(-.3, .3))
    add(st['bass'], t0, bass(m2f(BASSN[(b_ // 2) % 4]), 1.0), .38); add(st['bass'], t0 + 2.5 * B, bass(m2f(BASSN[(b_ // 2) % 4] + 12), .4), .22)
    for s in range(4): add(st['tick'], t0 + s * B, tick(2600 if s % 2 else 3100), .09)
S2, S3, S8, S9, S10 = C['s2'], 6.485, C['s8'], C['s9'], C['s10']
NB = W['nobody'] - .05; CA = W['cancelled']
Gn = {
 'tick':  curve([(0, 1), (S2, 1), (S2 + .3, .4), (NB, .4), (NB + .01, 0), (S9, 0), (S9 + .2, .8), (CA - .02, .8), (CA, 0), (DUR, 0)]),
 'pad':   curve([(0, .7), (NB, .7), (NB + .2, 1.1), (S3, .5), (S8, .5), (S8 + .3, 1), (S9, .8), (CA - .02, .8), (CA, 0), (DUR, 0)]),
 'kick':  curve([(0, 0), (S2 - .01, 0), (S2, .7), (NB, .7), (NB + .01, 0), (S3 - .01, 0), (S3, 1), (S9, 1), (S9 + .05, 0), (DUR, 0)]),
 'snare': curve([(0, 0), (S3 - .01, 0), (S3, 1), (S9, 1), (S9 + .05, 0), (DUR, 0)]),
 'hat':   curve([(0, .3), (S2, .6), (NB, .6), (NB + .01, 0), (S3 - .01, 0), (S3, 1), (S8, 1), (S8 + .1, .6), (S9, .6), (S9 + .05, 0), (DUR, 0)]),
 'shk':   curve([(0, 0), (S3 - .01, 0), (S3, 1), (S9, 1), (S9 + .05, 0), (DUR, 0)]),
 'bass':  curve([(0, 0), (S2, 0), (S2 + .01, .6), (NB, .6), (NB + .01, 0), (S3 - .01, 0), (S3, 1), (S9, 1), (S9 + .1, .5), (CA - .02, .5), (CA, 0), (DUR, 0)]),
 'pluck': curve([(0, .5), (NB, .5), (NB + .01, 0), (S3 - .01, 0), (S3, 1), (S9, 1), (S9 + .1, .5), (CA - .02, .5), (CA, 0), (DUR, 0)]),
 'keys':  curve([(0, 0), (S3 - .01, 0), (S3, 1), (S9, 1), (S9 + .1, .6), (CA - .02, .6), (CA, 0), (DUR, 0)]),
}
music = sum(st[k] * Gn[k][:, None] for k in Gn)
i0, i1 = int(S8 * SR), int(S9 * SR); seg = music[i0:i1].copy()          # the dark orbit sits under a low-pass that opens on each Done
op = np.clip((np.arange(i1 - i0) / SR - (W['done1'] - S8) + .2) / 1.6, 0, 1)[:, None]
music[i0:i1] = lp(seg, 700) * (1 - op) + seg * op
# ending: Fmaj9 on the mark, then a three-note bell motif on the tagline
for k, n in enumerate([41, 53, 57, 60, 64, 67]): add(music, W['brand'] - .02 + k * .012, ep(m2f(n), 5.0) * np.exp(-tv(5.0) / 2.4), .2 if n > 45 else .45)
add(music, W['brand'], pad([65, 69, 72, 76], DUR - W['brand']), .8)
for t0, n in [(W['less'], 76), (W['talk'] + .18, 79), (W['more'], 84)]:
    t = tv(2.5); add(music, t0, (sine(m2f(n), t) + .3 * sine(m2f(n) * 2.76, t) * np.exp(-t / .2)) * np.exp(-t / .8) * att(t), .07)
music = music + .22 * room(music, .9, 3.0)

# ================================================================ sound design
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

# S1: cards land, Join click, dive into the pill
for i in range(6): pop(i * .07 + .25, .2, 650 + 80 * i, [-.2, -.6, .6, .2, -.1, .7][i])
whoosh(.55, .9, .18, 3000, 300, -.7, .4)                         # giant cursor sweep
click(C['joinClick'], .45, .2)
riser(C['s2'] + .1, .7, .14); whoosh(C['s2'] + .2, .6, .38, 200, 7000, .5, -.3); pop(C['s2'] + .45, .25, 700)
# S2: Ava types, the team stacks up, the room goes quiet
for i in range(len('Same as last week.')): key(3.0 + (i + .5) / 20, .1)
for i in range(4): pop(3.62 + i * .22 + .05, .26, [880, 990, 1110, 760][i], [-.2, .2, .1, -.1][i])
thud(NB, .65, 70, 30); whoosh(NB + .2, 1.2, .14, 2500, 250, 0, 0)
# S3: box opens, voice-synced typing, send, collapse
whoosh(C['s3'] + .15, .6, .3, 400, 5000, -.3, .3)
for i in range(4): pop(C['s3'] + .55 + i * .07, .12, 1200 + 120 * i, -.3 + .2 * i)
for word, k in [('Now ', 'now'), ('Notion ', 'notion'), ('gives ', 'gives'), ('your ', 'your'), ('team ', 'team'), ('agents', 'agents')]:
    for i, ch in enumerate(word):
        if ch != ' ': key(W[k] - .02 + (i + .5) / 34, .14)
click(C['send'], .5); whoosh(C['send'] + .25, .45, .22, 4000, 600, .2, -.2); pop(C['send'] + .5, .22, 900)
# S4: agents fly in, the pick, the card becomes an avatar
for i in range(3): whoosh(C['s4'] + .2 + i * .1, .45, .2, 300, 4500, [-.8, 0, .8][i], [-.2, 0, .2][i])
click(C['pickClick'], .5); chime(C['pickClick'] + .03, .12, 81); whoosh(C['pickClick'] + .2, .5, .2, 500, 3000, 0, 0)
whoosh(C['s5'] + .25, .5, .18, 3000, 500, .3, -.4)
# S5: Read / Flag / Push, each word types, Stuck lands
for i, (k, kk) in enumerate([('read', 'every'), ('flag', 'whats'), ('push', 'it')]):
    pop(W[k], .32, [900, 1000, 1200][i], .3); chime(W[k] + .02, .06, [79, 81, 84][i], .3)
    for j in range(len(['every doc', 'what’s stuck', 'it forward'][i])): key(W[kk] - .04 + (j + .5) / 26, .08, .3)
pop(W['stuck'] + .22, .3, 600, .5); thud(W['stuck'] + .22, .25, 120, 60)
# S6/S7: the whip, the icons, the carousel, the checklist
whoosh(C['s6'], .55, .5, 300, 9000, -.9, .9); thud(C['s6'] + .05, .4)
for i in range(3): pop(W['three'] + i * .1, .28, 700 + 150 * i, -.3 + .3 * i)
whoosh(C['s7'] - .05, .55, .45, 300, 8000, .9, -.9)
pop(W['launch'], .25, 700); chime(W['drafted'] + .05, .14, 86)
for j in range(4): click(17.0 + j * .26 + .15, .22, .2); pop(17.0 + j * .26 + .16, .12, 1400 + 80 * j, .2)
# S8: into the dark, working, the camera flies, done done done
thud(S8, .75, 80, 30); whoosh(S8 - .1, 1.0, .22, 6000, 200, 0, 0)
for i in range(3): pop(W['working'] - .1 + i * .13, .22, 650 + 120 * i, [0, -.6, .6][i])
for i, (k, pn) in enumerate([('done1', 0), ('done2', -.6), ('done3', .6)]):
    whoosh(W[k] - .2, .5, .16, 600, 4000, -pn, pn); chime(W[k], .26, [79, 83, 86][i], pn); pop(W[k], .2, 1100 + 200 * i, pn)
pop(W['done3'] + .55, .2, 900)
# S9: back to paper, the call, the slide, cancelled
whoosh(S9 + .1, .7, .32, 200, 6000, -.5, .5); pop(S9 + .5, .28, 700)
click(C['drag0'], .4, .3); whoosh(C['drag0'] + .25, .42, .14, 1500, 600, .4, -.1)
t = tv(.5); bo = np.concatenate([sine(620, t[:int(.15 * SR)]), sine(415, t[:int(.3 * SR)])]); add(sfx, CA + .02, bo * np.minimum(1, np.arange(len(bo)) / 200) * np.exp(-np.arange(len(bo)) / SR / .35), .14, .2)
thud(CA, .55, 100, 42)
# S10: shrink to a dot, the mark arrives
whoosh(S10 + .15, .4, .2, 3000, 400, 0, 0); pop(S10 + .45, .28, 900)
thud(W['brand'], .6, 90, 36); whoosh(W['brand'] + .5, .5, .12, 500, 3000, -.2, .2)
sfx = sfx + .16 * room(sfx, .35, 1.5, 9)

# ================================================================ voice: one take, gentle compression, a touch of room
x, sr = sf.read(os.path.join(HERE, '..', 'vo', 'v3', 'vo_tight.wav'), dtype='float32')
if x.ndim > 1: x = x.mean(1)
if sr != SR: x = resample_poly(x, SR, sr).astype(np.float32)
x = hp(x, 90)
env = np.sqrt(np.convolve(x ** 2, np.ones(480) / 480, 'same')) + 1e-6; gc = np.minimum(1, (env / .08) ** -.35); x = x * gc   # ~1.5:1 above threshold
vo = np.zeros((N, 2), np.float32); add(vo, C['voOffset'], x, 1.0)
vo = vo + .05 * room(vo, .22, .9, 4, 5000)

# ================================================================ mix: music ducks ~7 dB under the voice
m = np.abs(vo).max(1); a_, r_ = np.exp(-1 / (.01 * SR)), np.exp(-1 / (.25 * SR)); e = np.empty_like(m); c = 0.
for k in range(len(m)): v = m[k]; c = a_ * c + (1 - a_) * v if v > c else r_ * c + (1 - r_) * v; e[k] = c
duck = 1 - .55 * np.clip(e / (np.percentile(e[e > 1e-4], 85) + 1e-9), 0, 1)
def rms(x, thr=None): x = x if thr is None else x[np.abs(x).max(1) > thr]; return float(np.sqrt(np.mean(x ** 2)) + 1e-9)
music *= 10 ** (-20 / 20) / rms(music[:int(S9 * SR)]); music *= duck[:, None]
sfx *= 10 ** (-23 / 20) / rms(sfx, 1e-3)
vo *= 10 ** (-15 / 20) / rms(vo, .01)
os.makedirs(os.path.join(HERE, 'build'), exist_ok=True)
for n, y in [('music', music), ('sfx', sfx), ('vo', vo), ('mix_raw', music + sfx + vo)]: sf.write(os.path.join(HERE, 'build', n + '.wav'), y.astype(np.float32), SR, subtype='FLOAT')
print('ok', round(float(np.abs(music + sfx + vo).max()), 2))
