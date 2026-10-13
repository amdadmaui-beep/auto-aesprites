# Score + SFX + VO mix for the AVE promo. Every sound is placed from cues.js.
import json, re, os, subprocess, sys, wave
import numpy as np
from scipy import signal

ROOT = os.path.dirname(os.path.abspath(__file__))
VO = os.path.join(ROOT, '..', 'vo')
SR = 48000
src = open(os.path.join(ROOT, 'cues.js')).read()
body = src[src.index('{'):src.rindex('}') + 1]
body = re.sub(r'//[^\n]*', '', body)
body = re.sub(r'([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:', r'\1"\2":', body)
C = json.loads(body)
DUR = C['dur']
N = int(DUR * SR)
rng = np.random.default_rng(7)

def buf(): return np.zeros((N, 2), np.float32)
music, sfx, vox = buf(), buf(), buf()

def tvec(d): return np.arange(int(d * SR)) / SR
def add(bus, t0, x, gain=1.0, pan=0.0):
    if x.ndim == 1:
        l = np.cos((pan + 1) * np.pi / 4); r = np.sin((pan + 1) * np.pi / 4)
        x = np.stack([x * l * 1.414, x * r * 1.414], 1)
    i = int(round(t0 * SR))
    if i < 0: x = x[-i:]; i = 0
    j = min(N, i + len(x))
    if j > i: bus[i:j] += (x[:j - i] * gain).astype(np.float32)
def lp(x, f, o=2): b, a = signal.butter(o, f / (SR / 2), 'low'); return signal.lfilter(b, a, x)
def hp(x, f, o=2): b, a = signal.butter(o, f / (SR / 2), 'high'); return signal.lfilter(b, a, x)
def bp(x, f1, f2, o=2): b, a = signal.butter(o, [f1 / (SR / 2), f2 / (SR / 2)], 'band'); return signal.lfilter(b, a, x)
def noise(d): return rng.standard_normal(int(d * SR))
def env_ad(d, a, dec):
    t = tvec(d); e = np.minimum(1, t / max(a, 1e-4)) * np.exp(-np.maximum(0, t - a) / dec); return e
def nfreq(n): return 440 * 2 ** ((n - 69) / 12)
NOTE = {k: i for i, k in enumerate(['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'])}
def m(s):  # 'D4' -> midi
    n = s[:-1]; o = int(s[-1]); n = n.replace('Bb', 'A#').replace('Eb', 'D#'); return 12 * (o + 1) + NOTE[n]

# ------------------------------------------------------------ instruments
def pad(t0, t1, notes, gain=.08, cutoff=1400, att=.5, rel=.8):
    d = t1 - t0 + rel; t = tvec(d); outL = np.zeros_like(t); outR = np.zeros_like(t)
    for n in notes:
        f = nfreq(m(n))
        for k, det in enumerate([-0.11, 0.0, 0.12]):
            ph = rng.random() * 2 * np.pi
            w = signal.sawtooth(2 * np.pi * f * (1 + det / 100 * 3) * t + ph) * .5 + np.sin(2 * np.pi * f * t + ph) * .5
            (outL if k != 2 else outR)[:] += w
            if k == 1: outR[:] += w * .7; outL[:] += w * .3
    e = np.minimum(1, t / att) * np.where(t > t1 - t0, np.exp(-(t - (t1 - t0)) / (rel / 3)), 1)
    x = np.stack([lp(outL, cutoff), lp(outR, cutoff)], 1) * e[:, None] / (len(notes) * 2)
    add(music, t0, x, gain)
def pluck(t0, n, gain=.12, pan=0., dec=.45, bright=1.):
    f = nfreq(m(n)) if isinstance(n, str) else n; t = tvec(dec * 4)
    x = np.sin(2 * np.pi * f * t) + .35 * bright * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t / .08) + .15 * bright * np.sin(2 * np.pi * 4.01 * f * t) * np.exp(-t / .03)
    add(music, t0, x * env_ad(dec * 4, .004, dec), gain, pan)
def kick(t0, gain=.5, bus=None):
    t = tvec(.5); f = 45 + 75 * np.exp(-t / .035); ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) * np.exp(-t / .22) + .3 * hp(noise(.5), 3000) * np.exp(-t / .004)
    add(music if bus is None else bus, t0, np.tanh(x * 1.4), gain)
def hat(t0, gain=.04, pan=.2, dec=.035):
    x = hp(noise(.2), 7000) * np.exp(-tvec(.2) / dec); add(music, t0, x, gain, pan)
def snap(t0, gain=.10):
    t = tvec(.3); x = bp(noise(.3), 1200, 3800) * np.exp(-t / .07); x += .5 * bp(noise(.3), 3000, 8000) * np.exp(-t / .012); add(music, t0, x, gain, -.1)
def sub(t0, d, n, gain=.18, glide=None):
    t = tvec(d); f = nfreq(m(n)) if isinstance(n, str) else n
    if glide: f = f * (1 + glide * np.exp(-t / .08))
    ph = 2 * np.pi * np.cumsum(np.full_like(t, f) if np.isscalar(f) else f) / SR
    e = np.minimum(1, t / .01) * np.minimum(1, (d - t) / .06)
    add(music, t0, np.tanh(1.6 * np.sin(ph)) * e, gain)

# ------------------------------------------------------------ sfx
def whoosh(t0, d=.45, gain=.3, f1=400, f2=4000, pan0=-.6, pan1=.6, peak=.6):
    t = tvec(d); x = noise(d); y = np.zeros_like(x); seg = 256
    for i in range(0, len(x), seg):  # time-varying bandpass
        p = i / len(x); fc = f1 * (f2 / f1) ** p
        y[i:i + seg] = bp(x[max(0, i - 512):i + seg], fc * .6, min(fc * 1.6, 20000))[-len(x[i:i + seg]):]
    e = np.where(t / d < peak, (t / d / peak) ** 2, ((1 - t / d) / (1 - peak)) ** 1.5)
    L = y * e * np.cos((np.linspace(pan0, pan1, len(t)) + 1) * np.pi / 4); R = y * e * np.sin((np.linspace(pan0, pan1, len(t)) + 1) * np.pi / 4)
    add(sfx, t0, np.stack([L, R], 1) * 1.4, gain)
def click(t0, gain=.3, f=2400, pan=0.):
    t = tvec(.06); x = bp(noise(.06), f * .7, f * 1.5) * np.exp(-t / .006) + .4 * np.sin(2 * np.pi * f * .5 * t) * np.exp(-t / .01)
    add(sfx, t0, x, gain, pan)
def tick(t0, gain=.1, pan=0.): click(t0, gain, 4200, pan)
def tone_click(t0, f, gain=.15, pan=0.):
    t = tvec(.25); x = np.sin(2 * np.pi * f * t) * np.exp(-t / .05) + .5 * np.sin(2 * np.pi * f * 2 * t) * np.exp(-t / .02)
    x += .4 * hp(noise(.25), 3000) * np.exp(-t / .003); add(sfx, t0, x, gain, pan)
def thump(t0, gain=.35, f0=110, f1=55, dec=.12):
    t = tvec(.4); f = f1 + (f0 - f1) * np.exp(-t / .03); x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / dec)
    x += .2 * lp(noise(.4), 800) * np.exp(-t / .02); add(sfx, t0, x, gain)
def slide(t0, gain=.25, d=.22, pan=-.3):
    t = tvec(d); x = bp(noise(d), 1500, 6000) * np.sin(np.pi * t / d) ** 1.5; add(sfx, t0, x, gain, pan); thump(t0 + d * .9, gain * .5, 180, 90, .05)
def chime(t0, freqs, gain=.25, step=.06, dec=.9):
    for k, f in enumerate(freqs):
        t = tvec(dec * 3); mod = np.sin(2 * np.pi * f * 3.5 * t) * 1.2 * np.exp(-t / .2)
        x = np.sin(2 * np.pi * f * t + mod) * np.exp(-t / dec)
        add(sfx, t0 + k * step, x, gain / len(freqs) * 1.6, (k - len(freqs) / 2) * .2)
def swish(t0, d=.5, gain=.2):
    t = tvec(d); x = bp(noise(d), 700, 3500) * np.sin(np.pi * t / d) ** 2; add(sfx, t0, x, gain, .3)
def riser(t0, t1, gain=.18):
    d = t1 - t0; t = tvec(d); f = 180 * (6 ** (t / d)); x = .5 * np.sin(2 * np.pi * np.cumsum(f) / SR) + .5 * signal.sawtooth(2 * np.pi * np.cumsum(f * 1.5) / SR) * .3
    nz = np.zeros_like(t); seg = 512; z = noise(d)
    for i in range(0, len(t), seg):
        fc = 600 * (12 ** (i / len(t))); nz[i:i + seg] = bp(z[max(0, i - 1024):i + seg], fc * .7, min(fc * 1.4, 20000))[-len(z[i:i + seg]):]
    e = (t / d) ** 2.2
    add(sfx, t0, lp(x, 3000) * e * .5 + nz * e, gain)
def scrub(t0, t1, gain=.12):
    t = t0
    while t < t1:
        p = (t - t0) / (t1 - t0); sp = np.sin(np.pi * p)
        click(t, gain * (.4 + .6 * sp), 1800 + 1600 * sp, -.2 + .4 * p); t += .045 - .025 * sp
def bass_hit(t0, gain=.9):
    t = tvec(2.2); f = 43.65 * (1 + 1.4 * np.exp(-t / .06)); x = np.sin(2 * np.pi * np.cumsum(f) / SR)
    x = np.tanh(2.0 * x) * np.exp(-t / .45)
    x += .6 * lp(noise(2.2), 1800) * np.exp(-t / .05) + .3 * hp(noise(2.2), 4000) * np.exp(-t / .015)
    add(sfx, t0, x, gain)
def reverse_swell(t0, t1, gain=.25):
    d = t1 - t0; t = tvec(d); x = lp(noise(d), 2500) * (t / d) ** 3 + .3 * np.sin(2 * np.pi * 87.3 * t) * (t / d) ** 2
    add(sfx, t0, x, gain)
def room(t0, t1, gain=.02):
    d = t1 - t0; x = lp(noise(d), 500); e = np.minimum(1, tvec(d) / .4) * np.minimum(1, (d - tvec(d)) / .4); add(sfx, t0, np.stack([x * e, lp(noise(d), 500) * e], 1), gain)

# ------------------------------------------------------------ score
beats = []
# section A: intro + hook (sparse, warm)
pad(0.0, 2.0, ['D3', 'A3', 'C4', 'E4', 'F4'], .055, 900, att=1.2)
pad(2.0, 3.5, ['A#2', 'D3', 'F3', 'A3', 'C4'], .06, 1100)
for i, n in enumerate(['A4', 'F4', 'C5', 'A4']): pluck(1.5 + i * .5, n, .045, -.2 + i * .13, .5)
# section B: cards + raw->edit (half-time groove)
pad(3.5, 6.0, ['F3', 'A3', 'C4', 'E4'], .06, 1500)
pad(6.0, 8.0, ['C3', 'E3', 'G3', 'D4'], .06, 1700)
for b in np.arange(3.5, 8.0, .5):
    if (b - 3.5) % 1.0 == 0: kick(b, .34)
    hat(b + .25, .028)
roots = {3.5: 'F1', 4.0: 'F1', 5.0: 'F1', 6.0: 'C2', 7.0: 'C2'}
for t0, n in [(3.5, 'F1'), (4.5, 'F1'), (5.5, 'A1'), (6.0, 'C2'), (7.0, 'C2'), (7.5, 'E2')]: sub(t0, .45, n, .14)
arp = ['F4', 'A4', 'C5', 'E5', 'C5', 'A4', 'G4', 'C5', 'E5', 'G5', 'E5', 'D5', 'C5', 'G4', 'E4', 'D4', 'E4', 'G4']
for i, b in enumerate(np.arange(3.5, 8.0, .25)): pluck(b, arp[i % len(arp)], .026 + .01 * (i % 2 == 0), .25 * np.sin(i), .25)
# section C: dashboard (four-on-floor, light)
pad(8.0, 10.0, ['D3', 'F3', 'A3', 'C4', 'E4'], .06, 2000)
pad(10.0, 11.5, ['A#2', 'D3', 'F3', 'A3', 'C4'], .06, 2200)
for b in np.arange(8.0, 11.5, .5):
    kick(b, .36)
    if (b - 8.0) % 1.0 == .5: snap(b, .07)
    for s in (0, .25): hat(b + s + .125, .022 if s else .03, .25)
for i, b in enumerate(np.arange(8.0, 11.5, .5)): sub(b, .42, ['D2', 'D2', 'D2', 'F2', 'A#1', 'A#1', 'C2'][i % 7] if b < 10 else 'A#1', .15)
arp2 = ['D5', 'A4', 'F4', 'A4', 'E5', 'A4', 'F4', 'A4', 'C5', 'A4', 'F4', 'A4', 'D5', 'F5', 'E5', 'C5']
for i, b in enumerate(np.arange(8.0, 11.5, .25)): pluck(b, arp2[i % 16], .022, .3 * np.sin(i * 1.3), .22)
# section D: range (drive + riser into the break)
pad(11.5, 13.0, ['G2', 'D3', 'F3', 'A#3', 'D4'], .07, 2600)
for b in np.arange(11.5, 13.0, .5):
    kick(b, .4); snap(b + .5, .06) if (b - 11.5) % 1.0 == 0 else None
    for s in (0, .125, .25, .375): hat(b + s, .02, -.2 + s)
for b in np.arange(11.5, 13.0, .5): sub(b, .42, 'G1', .16)
riser(12.35, 13.0, .10)
# section E: break -> hit
pad(13.0, 15.0, ['D2', 'A2', 'D3', 'E3'], .05, 600, att=.3, rel=.3)
sub(13.0, 1.95, 'D1', .10)
for b in np.arange(13.5, 15.0, .5): hat(b, .012, 0, .02)
# section F: resolution after the hit
pad(C['hit'], 18.0, ['F2', 'C3', 'A3', 'E4', 'G4'], .085, 2400, att=.05, rel=.5)
for i, (dt, n) in enumerate([(.5, 'A4'), (1.0, 'C5'), (1.25, 'E5'), (1.5, 'G5'), (2.0, 'F5'), (2.5, 'E5'), (2.75, 'C5')]):
    pluck(C['hit'] + dt, n, .035, -.3 + i * .1, .5)
kick(C['hit'] + 1.0, .18); kick(C['hit'] + 2.0, .14)
# beat grid (measured from the kick stem below)

# ------------------------------------------------------------ sfx timeline
room(0, 3.6, .010)
swish(C['catIn'], C['land'] - C['catIn'], .14); thump(C['land'], .32, 120, 60, .1); swish(C['tailFlick'], .3, .04)
for k in range(0, 13, 2): tick(C['micro'] + k * .028, .05, -.3)
tone_click(C['got'], 880, .11, -.2); tone_click(C['got'] + .075, 1046.5, .07, -.1)
tone_click(C['worth'], 987.8, .10, 0)
whoosh(C['watching'] - .02, .38, .07, 1500, 7000, .4, -.1, .3); chime(C['watching'] + .02, [1318.5, 1975.5], .08, .03, .5)
swish(C['watching'] + .08, .3, .06)
whoosh(C['hookOut'] - .05, .32, .10, 900, 5000, 0, .3, .7)
for k in ('card1', 'card2', 'card3'): slide(C[k] - .03, .22, .24, -.4)
click(C['card1'] + .55, .08, 3000)
whoosh(C['phoneIn'] - .05, .5, .22, 300, 3000, .3, -.2, .6)
click(C['tap'], .30, 3200, .4); tone_click(C['tap'] + .01, 1760, .06, .4)
riser(C['frame'], C['aveEdit'] + .02, .10)
for k in range(3): tone_click(C['subs'] + k * .1, 1318.5 + k * 110, .045)
swish(C['hiword'], .26, .08); whoosh(C['motion'], .2, .07, 2000, 9000, -.2, .3, .3)
tone_click(C['wave'], 1567.98, .06, .2); slide(C['visual'], .10, .18, -.3)
chime(C['aveEdit'], [1046.5, 1318.5, 1568, 2093], .22, .035, .7)
whoosh(C['dashIn'] - .05, .5, .16, 3000, 400, .2, -.2, .25)
for i in range(7): tick(C['dashIn'] + .05 + i * .045, .035, -.6 + i * .2)
scrub(C['scrub'], C['clipSel'] - .05, .07)
click(C['clipSel'], .34, 2600, -.3)
whoosh(C['chipFly'], C['capsIn'] - C['chipFly'] + .05, .07, 800, 4000, -.5, .1, .6)
click(C['capsIn'], .12, 3000)
for k in range(4): tick(C['capsIn'] + .12 + k * .1, .08, .1)
for k in range(4): tone_click(C['motionOn'] + .04 + k * .075, 1174.7 * 2 ** (k / 12 * 3), .05, -.4)
thump(C['soundOn'], .13, 90, 50, .2)
thump(C['tagImpact'], .30, 140, 45, .18); click(C['tagClick'], .26, 3400); whoosh(C['tagWhoosh'], .3, .16, 600, 6000, -.4, .4, .5)
tone_click(C['visualOn'] + .06, 784, .07, .3); slide(C['readyIn'], .10, .2, .4)
for k in ('plat1', 'plat2', 'plat3'): tone_click(C[k], 1318.5, .09, .5); tone_click(C[k] + .045, 1975.5, .06, .5)
chime(C['ready'], [1046.5, 1318.5, 1568, 2093, 2637], .32, .045, 1.1)
whoosh(C['p1'] - .14, .3, .30, 300, 5000, -.8, .8, .55); thump(C['p1punch'], .26, 160, 60, .08); click(C['p1punch'], .1, 1800)
whoosh(C['p2'] - .14, .3, .28, 300, 5000, .8, -.8, .55); click(C['p2switch'], .14, 2200, .3); thump(C['p2switch'], .1, 200, 120, .04)
whoosh(C['p3'] - .14, .3, .28, 300, 5000, -.8, .8, .55); tone_click(C['p3'] + .2, 1400, .05, .5); click(C['p3click'], .26, 2800, .5)
whoosh(C['S7'] - .1, .35, .22, 5000, 200, 0, 0, .3)
thump(C['youCreate'], .08, 70, 50, .3)
reverse_swell(C['hit'] - .45, C['hit'], .18)
bass_hit(C['hit'], .42)
whoosh(C['S8'], .46, .14, 4000, 600, .4, -.3, .4)
tick(C['S8'] + .2, .05)
chime(C['cta'], [1568, 2349.3], .16, .07, .5); click(C['cta'], .08, 2600)
swish(C['wave1'], .5, .03)

# ------------------------------------------------------------ voice
def readwav(p):
    w = wave.open(p); x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768; return x
def vo_file(name, tempo=1.0):
    p = os.path.join(VO, name + '.wav')
    if tempo != 1.0:
        q = os.path.join(ROOT, 'build', f'{name}_t{tempo}.wav'); os.makedirs(os.path.dirname(q), exist_ok=True)
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', p, '-af', f'atempo={tempo}', '-ar', str(SR), '-ac', '1', q], check=True); p = q
    x = readwav(p); x = hp(x, 85, 2)
    # gentle presence + level
    x = x + .25 * bp(x, 2500, 6000)
    return x
def place(name, seg, onset, target, tempo=1.0, gain=1.0):
    x = vo_file(name, tempo); a, b = seg[0] / tempo, seg[1] / tempo
    i, j = int(a * SR), min(len(x), int(b * SR)); y = x[i:j].copy()
    f = int(.012 * SR); y[:f] *= np.linspace(0, 1, f); y[-f:] *= np.linspace(1, 0, f)
    add(vox, target - (onset - seg[0]) / tempo, y, gain)
place('vo1', (0, 2.14), .04, C['got'])
place('vo2', (0, .76), .04, C['card1'] + .02)
place('vo2', (.88, 1.92), .95, C['card2'] + .02)
place('vo2', (2.0, 2.98), 2.07, C['card3'] + .02)
place('vo3', (0, 3.45), .06, C['line1'], 1.12)
place('vo4', (0, .66), .04, C['clipSel'] + .03)
place('vo4', (.96, 1.80), 1.03, C['capsIn'] + .1)
place('vo4', (2.06, 3.0), 2.12, C['motionOn'] + .02)
place('vo4', (3.1, 4.28), 3.18, C['readyIn'] - .06)
place('vo5', (0, 1.32), .12, C['youCreate'])
place('vo5', (1.45, 2.98), 2.37, C['hit'])
place('vo6b', (0, 2.19), .05, C['S8'] + .17, 1.06)

# ------------------------------------------------------------ mix
def rms_env(x, win=.03):
    m = np.abs(x).max(1); k = int(win * SR); e = np.sqrt(np.convolve(m ** 2, np.ones(k) / k, 'same')); return e
ve = rms_env(vox); act = np.clip(ve / 0.02, 0, 1)
# smooth: fast attack, slow release
g = np.zeros_like(act); a_c = np.exp(-1 / (.03 * SR)); r_c = np.exp(-1 / (.28 * SR)); s = 0
for i in range(len(act)):
    v = act[i]; c = a_c if v > s else r_c; s = c * s + (1 - c) * v; g[i] = s
duck = 1 - .62 * g  # ~ -8.5 dB under voice
sec = np.ones(N, np.float32)
for t0, t1, gv in [(3.5, 11.5, .5), (11.5, 13.0, .62), (15.25, 18.0, .75)]:
    sec[int(t0 * SR):int(t1 * SR)] = gv
sec = np.convolve(sec, np.ones(2400) / 2400, 'same')
duck = duck * sec
vnorm = .30 / (np.percentile(np.abs(vox[np.abs(vox).max(1) > 1e-3]).max(1), 99) + 1e-9)
mix = music * duck[:, None] * 1.0 + sfx * (1 - .25 * g)[:, None] + vox * vnorm
# end fade
fo = int(.35 * SR); mix[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 1.5
mix = np.tanh(mix * 1.1) / 1.1
os.makedirs(os.path.join(ROOT, 'build'), exist_ok=True)
def writewav(p, x):
    y = np.clip(x, -1, 1); w = wave.open(p, 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((y * 32767).astype(np.int16).tobytes()); w.close()
writewav(os.path.join(ROOT, 'build', 'mix_raw.wav'), mix)
writewav(os.path.join(ROOT, 'build', 'stem_music.wav'), music)

# beats.json measured from the kick stem (onset detection on a kick-only render)
kb = np.zeros((N, 2), np.float32)
kick_times = [b for b in np.arange(3.5, 8.0, 1.0)] + list(np.arange(8.0, 13.0, .5)) + [C['hit'], C['hit'] + 1.0, C['hit'] + 2.0]
for b in kick_times: kick(b, 1.0, kb)
k = np.abs(hp(kb[:, 0], 1500)); env = np.convolve(k, np.ones(96) / 96, 'same')
pk, _ = signal.find_peaks(env, height=env.max() * .25, distance=int(.2 * SR))
on = [float(round(p / SR - .001, 3)) for p in pk]
grid = [round(x * .5, 3) for x in range(0, 30)] + [round(C['hit'] + x * .5, 3) for x in range(0, 6)]
json.dump({'bpm': C['bpm'], 'beats': grid, 'downbeats': [round(x * 2.0, 3) for x in range(8)] + [C['hit']], 'kick_onsets': on},
          open(os.path.join(ROOT, 'beats.json'), 'w'), indent=1)
print('kicks detected', len(on), 'of', len(kick_times))

if '--report' in sys.argv:
    vv = vox * vnorm; mm = music * duck[:, None]; ss = sfx * (1 - .25 * g)[:, None]
    def db(x): return 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9)
    for a, b, name in [(0, 1.5, 'S1'), (1.5, 3.5, 'S2'), (3.5, 5.5, 'S3'), (5.5, 8, 'S4'), (8, 11.5, 'S5'), (11.5, 13, 'S6'), (13, 15.25, 'S7'), (15.25, 18, 'S8')]:
        i, j = int(a * SR), int(b * SR)
        print(f"{name}: voice {db(vv[i:j]):6.1f}  music {db(mm[i:j]):6.1f}  sfx {db(ss[i:j]):6.1f} dB")
    on = np.abs(vv).max(1) > .01
    idx = np.nonzero(np.diff(on.astype(int)) == 1)[0] / SR
    print('voice onsets', [round(x, 2) for x in idx if True][:40])
