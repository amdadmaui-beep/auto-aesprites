# Notion spec spot: original score (104 BPM, F major), synthesized UI sound design, Fish Audio voiceover.
# Every cue is read from cues.js, the same timeline the picture uses.
# Writes build/music.wav, build/sfx.wav, build/vo.wav, build/mix_raw.wav
import json, os, re
import numpy as np, soundfile as sf
from scipy import signal
from scipy.signal import fftconvolve, resample_poly

HERE = os.path.dirname(os.path.abspath(__file__)); SR = 48000
src = open(os.path.join(HERE, 'cues.js')).read(); C = json.loads(src[src.index('{'):src.rindex('}') + 1])
DUR = C['dur']; N = int(DUR * SR); SC = C['scene']; rng = np.random.default_rng(7)
BEAT = 60 / C['bpm']; S16 = BEAT / 4

def tv(d): return np.arange(int(d * SR)) / SR
def lp(x, f, o=2): b, a = signal.butter(o, min(f, SR / 2 - 200) / (SR / 2), 'low'); return signal.lfilter(b, a, x, axis=0)
def hp(x, f, o=2): b, a = signal.butter(o, f / (SR / 2), 'high'); return signal.lfilter(b, a, x, axis=0)
def bp(x, f1, f2, o=2): b, a = signal.butter(o, [f1 / (SR / 2), min(f2, SR / 2 - 200) / (SR / 2)], 'band'); return signal.lfilter(b, a, x, axis=0)
def osc(f): return np.sin(2 * np.pi * np.cumsum(np.broadcast_to(f, f.shape if hasattr(f, 'shape') else ())) / SR)
def sine(f, t): return np.sin(2 * np.pi * f * t)
def att(t, a=.003): return np.minimum(1, t / a)
def panst(x, pan): return np.stack([x * np.cos((pan + 1) * np.pi / 4), x * np.sin((pan + 1) * np.pi / 4)], 1) * 1.414
def add(buf, t0, x, g=1., pan=0.):
    if x.ndim == 1: x = panst(x, pan)
    i = int(round(t0 * SR))
    if i < 0: x = x[-i:]; i = 0
    j = min(len(buf), i + len(x))
    if j > i: buf[i:j] += (x[:j - i] * g).astype(np.float32)
def room(x, dec=.6, length=2.5, seed=3, lpf=6000):
    r = np.random.default_rng(seed); t = tv(length); out = []
    for c in (0, 1):
        ir = lp(r.standard_normal(len(t)) * np.exp(-t / dec), lpf); ir /= np.sqrt((ir ** 2).sum())
        out.append(fftconvolve(x[:, c], ir)[:len(x)])
    return np.stack(out, 1).astype(np.float32)
def m2f(m): return 440 * 2 ** ((m - 69) / 12)

# ================================================================ score
mus = {k: np.zeros((N, 2), np.float32) for k in ['keys', 'pluck', 'bass', 'kick', 'clap', 'hat', 'pad', 'bell']}
PROG = [[53, 57, 60, 64], [50, 53, 57, 60, 64], [46, 50, 53, 57], [48, 52, 55, 60]]   # Fmaj7  Dm9  Bbmaj7  C
BASS = [41, 38, 34, 36]
def ep(f, d):     # soft electric piano
    t = tv(d); x = sine(f, t) + .35 * sine(2 * f, t) * np.exp(-t / .3) + .12 * sine(3.01 * f, t) * np.exp(-t / .12)
    return x * np.exp(-t / 1.1) * att(t, .004)
def pluck(f, d=.45):
    t = tv(d); x = (sine(f, t) + .5 * sine(2 * f, t) * np.exp(-t / .06) + .2 * sine(4 * f, t) * np.exp(-t / .02)) * np.exp(-t / .16) * att(t, .002)
    return lp(x, 5000)
def kick(d=.4):
    t = tv(d); f = 48 + 110 * np.exp(-t / .03); return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / .2) + .3 * lp(rng.standard_normal(len(t)), 2000) * np.exp(-t / .004)) * att(t, .001)
def clap():
    t = tv(.35); n = rng.standard_normal(len(t)); e = sum(np.exp(-np.maximum(0, t - k * .009) / .006) * (t >= k * .009) for k in range(3)) + .6 * np.exp(-t / .09)
    return bp(n * e, 900, 5000)
def hat(d=.06):
    t = tv(d); return hp(rng.standard_normal(len(t)), 7000) * np.exp(-t / .018)
def padv(notes, d):
    t = tv(d); x = sum(sum(np.sin(2 * np.pi * m2f(n) * (1 + dt) * t + rng.uniform(0, 6)) for dt in (-.004, 0, .004)) for n in notes)
    return lp(x * np.minimum(1, t / .6) * np.minimum(1, (d - t) / .6), 2400) / 8
def bass(f, d):
    t = tv(d); x = np.tanh(1.6 * (sine(f, t) + .3 * sine(2 * f, t))) * np.exp(-t / .5) * att(t, .004); return lp(x, 700)
bar = 4 * BEAT; nbars = int(DUR / bar) + 2
ARP = [0, 2, 1, 3, 2, 1, 3, 2]
for b in range(nbars):
    t0 = b * bar; ch = PROG[b % 4]
    add(mus['pad'], t0, padv([n + 12 for n in ch[:3]], bar + .5), .5)
    for k, off in enumerate([0, 1.5, 2.5]):
        for n in ch: add(mus['keys'], t0 + off * BEAT + k * .004, ep(m2f(n), 1.6), .12, rng.uniform(-.3, .3))
    for s in range(8): add(mus['pluck'], t0 + s * BEAT / 2, pluck(m2f(ch[ARP[s] % len(ch)] + 24)), .16, .5 * np.sin(s))
    for s, d in [(0, 1.4), (1.5, .4), (2, 1.0), (3.5, .45)]: add(mus['bass'], t0 + s * BEAT, bass(m2f(BASS[b % 4] + (12 if s == 3.5 else 0)), d), .32)
    for s in (0, 2): add(mus['kick'], t0 + s * BEAT, kick(), .7)
    add(mus['kick'], t0 + 2.75 * BEAT, kick(), .35)
    for s in (1, 3): add(mus['clap'], t0 + s * BEAT, clap(), .22)
    for s in range(16): add(mus['hat'], t0 + s * S16 + (S16 * .12 if s % 2 else 0), hat(), .09 if s % 2 else .05, .3)
# section automation (per stem gain curves)
def curve(pts):
    x = np.array([p[0] for p in pts]); y = np.array([p[1] for p in pts]); return np.interp(np.arange(N) / SR, x, y).astype(np.float32)
NB, CA = C['nobody'], C['cancelled']
G = {
 'keys':  curve([(0, .8), (NB - .1, .8), (NB, .0), (SC['C'] - .3, 0), (SC['C'], .9), (SC['G'], .9), (SC['G'] + .2, .3), (SC['H'], .4), (CA - .05, .4), (CA, 0), (SC['I'] + .5, 0), (DUR, 0)]),
 'pluck': curve([(0, .9), (NB - .1, .9), (NB, 0), (SC['C'] - .2, 0), (SC['C'], 1), (SC['G'], 1), (SC['G'] + .2, .7), (SC['H'], .6), (CA - .05, .6), (CA, 0), (DUR, 0)]),
 'bass':  curve([(0, 0), (SC['B'] - .05, 0), (SC['B'], .8), (NB - .1, .8), (NB, 0), (SC['C'], 0), (SC['C'] + .05, 1), (SC['H'] - .1, 1), (SC['H'], .5), (CA - .05, .5), (CA, 0), (DUR, 0)]),
 'kick':  curve([(0, 0), (SC['B'] - .05, 0), (SC['B'], .8), (NB - .1, .8), (NB, 0), (SC['C'] + .2, 0), (SC['C'] + .25, 1), (SC['H'] - .1, 1), (SC['H'], 0), (DUR, 0)]),
 'clap':  curve([(0, 0), (SC['D'] - .05, 0), (SC['D'], 1), (SC['H'] - .1, 1), (SC['H'], 0), (DUR, 0)]),
 'hat':   curve([(0, .6), (NB - .1, .6), (NB, 0), (SC['C'] - .5, 0), (SC['C'], 1), (SC['H'] - .1, 1), (SC['H'], .5), (CA - .05, .5), (CA, 0), (DUR, 0)]),
 'pad':   curve([(0, .6), (NB, .6), (NB + .2, 1.2), (SC['C'], .6), (SC['G'], .6), (SC['G'] + .3, 1.0), (SC['H'], .6), (CA - .05, .6), (CA, 0), (DUR, 0)]),
}
music = sum(mus[k] * G[k][:, None] for k in G)
# the dark orbit scene sits under a low-pass that opens on each Done
cut = (SC['G'] <= np.arange(N) / SR) & (np.arange(N) / SR < SC['H'])
i0, i1 = int(SC['G'] * SR), int(SC['H'] * SR); seg = music[i0:i1]
music[i0:i1] = .6 * lp(seg, 900) + .4 * seg * np.clip((np.arange(i1 - i0) / SR - (C['dones'][0] - SC['G'])) / 1.2, 0, 1)[:, None]
# the ending: one ringing Fmaj9 on the logo, with bells
endc = [41, 53, 57, 60, 64, 67]
for k, n in enumerate(endc): add(music, C['logo'] + k * .012, ep(m2f(n), 5.5) * np.exp(-tv(5.5) / 2.2), .22 if n > 45 else .5)
add(music, C['logo'], padv([65, 69, 72, 76], DUR - C['logo']), .7)
for k, n in enumerate([72, 76, 79, 84]):
    t = tv(2.5); add(music, C['logo'] + .1 + k * BEAT / 2, (sine(m2f(n), t) + .3 * sine(m2f(n) * 2.76, t) * np.exp(-t / .2)) * np.exp(-t / .7) * att(t), .08, [-.4, .3, -.2, .4][k])
music = music + .25 * room(music, .9, 3.0)

# ================================================================ sound design
sfx = np.zeros((N, 2), np.float32)
def pop(t0, g=.35, f=900, pan=0.):
    t = tv(.12); fr = f * (1 + 1.2 * np.exp(-t / .012)); x = np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-t / .03) * att(t, .001)
    add(sfx, t0, lp(x, 6000), g, pan)
def click(t0, g=.35, pan=0.):
    t = tv(.05); x = bp(rng.standard_normal(len(t)), 1500, 7000) * np.exp(-t / .004) + .5 * sine(2400, t) * np.exp(-t / .006)
    add(sfx, t0, x, g, pan)
def key(t0, g=.18, pan=0.):
    t = tv(.06); x = bp(rng.standard_normal(len(t)), 2000, 8000) * np.exp(-t / .006) + .4 * sine(rng.uniform(300, 420), t) * np.exp(-t / .01)
    add(sfx, t0, x, g * rng.uniform(.7, 1.1), pan + rng.uniform(-.15, .15))
def whoosh(t0, d=.5, g=.3, f0=300, f1=4000, p0=-.5, p1=.5):
    t = tv(d); x = rng.standard_normal(len(t)); y = np.zeros_like(x); seg = 512
    for i in range(0, len(x), seg):
        fc = f0 * (f1 / f0) ** (i / len(x)); y[i:i + seg] = bp(x[max(0, i - 2048):i + seg], fc / 1.8, min(fc * 1.8, 16000))[-len(x[i:i + seg]):]
    e = np.sin(np.pi * t / d) ** 2; pn = np.linspace(p0, p1, len(t))
    add(sfx, t0 - d / 2, np.stack([y * e * np.cos((pn + 1) * np.pi / 4), y * e * np.sin((pn + 1) * np.pi / 4)], 1) * 1.6, g)
def ding(t0, g=.25, n=84, pan=0.):
    t = tv(1.4); f = m2f(n); x = (sine(f, t) + .4 * sine(f * 2.0, t) * np.exp(-t / .3) + .2 * sine(f * 3.01, t) * np.exp(-t / .08)) * np.exp(-t / .45) * att(t, .002)
    add(sfx, t0, x, g, pan)
def thud(t0, g=.5, f0=90, f1=40):
    t = tv(.6); f = f1 + (f0 - f1) * np.exp(-t / .05); add(sfx, t0, np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / .22) * att(t, .002), g)
def shimmer(t0, d=1.2, g=.06):
    t = tv(d); x = sum(sine(m2f(n), t) * (.5 + .5 * np.sin(2 * np.pi * (6 + k) * t)) for k, n in enumerate([84, 88, 91, 96])); add(sfx, t0, x * np.sin(np.pi * t / d) ** 2, g)

# A: meetings pop in, the Join click
for i, c in enumerate(C['cardsIn']): pop(c + .08, .22, 700 + 90 * i, [-.6, .1, .2, .6, -.1, .7][i])
click(C['joinClick'], .4, .2); pop(C['joinClick'] + .02, .15, 1300, .2)
whoosh(SC['B'], .7, .35, 200, 6000, .5, -.5)
# B: bubbles, then the room goes quiet for "Nobody doing."
for i, b in enumerate(C['bubbles']): pop(b + .04, .3, [880, 990, 1110, 1180][i], [-.2, .2, -.1, .1][i])
for k in range(5): click(C['bubbles'][3] + .35 + k * .28, .05, .3)
thud(NB, .55, 70, 35); whoosh(NB + .1, 1.2, .18, 2000, 300, 0, 0)
# C: prompt box, typing, send
whoosh(SC['C'] + .05, .6, .28, 400, 5000, -.3, .3); pop(SC['C'] + .2, .25, 600)
for i in range(4): pop(SC['C'] + .5 + i * .08, .14, 1200 + 120 * i, -.3 + .2 * i)
T = C['type']; txt = T['text']
for i, ch in enumerate(txt):
    if ch != ' ': key(T['t0'] + (i + .5) / len(txt) * (T['t1'] - T['t0']), .16)
click(C['send'], .45); pop(C['send'] + .03, .3, 1500); shimmer(C['send'] + .1, .9, .05)
# D: agent cards, the pick, the shrink
for i, a in enumerate(C['agentCards']): pop(a + .1, .3, 800 + 150 * i, [-.5, 0, .5][i])
click(C['pickClick'], .45); ding(C['pickClick'] + .05, .14, 81)
whoosh(SC['E'] - .05, .5, .2, 3000, 500, .3, -.3)
# E: Read / Flag / Push
for i, c in enumerate(C['chips']): pop(c + .05, .35, [900, 1000, 1200][i], .3); ding(c + .06, .07, [79, 81, 84][i], .3)
pop(C['stuckTag'] + .1, .3, 600, .5); thud(C['stuckTag'] + .1, .2, 120, 60)
# F1/F2: whip into the streaks, risk icons, the plan writes itself
whoosh(SC['F1'], .6, .45, 300, 9000, -.8, .8); thud(SC['F1'] + .05, .35)
for i in range(3): pop(C['risks'] + .05 + i * .12, .3, 700 + 150 * i, -.3 + .3 * i)
whoosh(C['risks'] + .6, .5, .15, 800, 5000, .2, .6)
whoosh(SC['F2'], .6, .4, 300, 8000, .8, -.8)
pop(C['plan'] + .05, .3, 700); ding(C['plan'] + .35, .14, 86)
for j, c in enumerate(C['planChecks']): click(c + .15, .25, .2); pop(c + .16, .14, 1400 + 80 * j, .2)
# G: dark orbit
thud(SC['G'], .7, 80, 32); whoosh(SC['G'] - .05, 1.0, .25, 6000, 200, 0, 0)
for i in range(3): pop(C['working'] - .1 + i * .15, .22, 650 + 120 * i, [0, -.6, .6][i])
for i, d in enumerate(C['dones']): ding(d, .3, [79, 83, 86][i], [0, -.5, .5][i]); pop(d, .2, 1100 + 200 * i, [0, -.5, .5][i])
pop(C['dones'][2] + .35, .2, 900)
# H: the meeting, the hang-up
whoosh(SC['H'] - .05, .7, .35, 200, 6000, -.5, .5); pop(C['meetPill'] + .1, .3, 700)
click(C['hangClick'], .5, .3)
t = tv(.5); bo = np.concatenate([sine(620, t[:int(.16 * SR)]), sine(440, t[:int(.3 * SR)])]); add(sfx, CA + .02, bo * np.minimum(1, np.arange(len(bo)) / 200) * np.exp(-np.arange(len(bo)) / SR / .35), .16, .2)
thud(CA, .5, 100, 45)
# I: end card
pop(C['endDot'], .3, 900); thud(C['logo'], .6, 90, 38); shimmer(C['logo'], 2.0, .05)
whoosh(C['word'] + .1, .5, .12, 500, 3000, -.2, .2)
sfx = sfx + .18 * room(sfx, .35, 1.5, 9)

# ================================================================ voiceover
vo = np.zeros((N, 2), np.float32)
for name, t0 in C['vo']:
    x, sr = sf.read(os.path.join(HERE, '..', 'vo', name + '.wav'), dtype='float32')
    if x.ndim > 1: x = x.mean(1)
    if sr != SR: x = resample_poly(x, SR, sr).astype(np.float32)
    x = hp(x, 80); x = x / (np.sqrt(np.mean(x[np.abs(x) > .02] ** 2)) + 1e-9) * .12
    add(vo, t0, x, 1.0, 0.)
vo = vo + .06 * room(vo, .25, 1.0, 4, 5000)

# ================================================================ mix: music ducks ~8 dB under the voice
def env(x, a_s=.01, r_s=.25):
    m = np.abs(x).max(1); w = int(.02 * SR); m = np.convolve(m, np.ones(w) / w, 'same')
    a = np.exp(-1 / (a_s * SR)); r = np.exp(-1 / (r_s * SR)); e = np.empty_like(m); c = 0.
    for k in range(len(m)): v = m[k]; c = a * c + (1 - a) * v if v > c else r * c + (1 - r) * v; e[k] = c
    return e
ev = env(vo); duck = 1 - .6 * np.clip(ev / (np.percentile(ev[ev > 1e-4], 90) + 1e-9), 0, 1)
def rms(x): return float(np.sqrt(np.mean(x ** 2)) + 1e-9)
music *= (10 ** (-21 / 20) / rms(music[:int(SC['I'] * SR)])) * duck[:, None]
sfx *= 10 ** (-22 / 20) / rms(sfx[np.abs(sfx).max(1) > 1e-3])
vo *= 10 ** (-15 / 20) / rms(vo[np.abs(vo).max(1) > .01])
mix = music + sfx + vo
pk = np.abs(mix).max(); g = min(1., .99 / pk) if pk > 2.5 else 1.  # peaks are caught by alimiter at the mux; music, sfx, vo, mix = music * g, sfx * g, vo * g, mix * g
os.makedirs(os.path.join(HERE, 'build'), exist_ok=True)
for n, x in [('music', music), ('sfx', sfx), ('vo', vo), ('mix_raw', mix)]: sf.write(os.path.join(HERE, 'build', n + '.wav'), x.astype(np.float32), SR, subtype='FLOAT')
print('peak', round(pk, 2), 'written')
