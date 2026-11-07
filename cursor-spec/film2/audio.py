# Cursor spec V2: original 120 BPM score + "creamy" sound design, placed from cues.js.
# Writes build/music.wav, build/sfx.wav, build/mix_raw.wav (music + sfx), build/nomusic_raw.wav (sfx only).
# Every sound is synthesised here. No samples, no copied music.
# Design rule for "creamy": round low-mid bodies, soft transients, nothing broadband or hissy above ~4 kHz
# (broadband noise is what reads as "ripping paper").
import json, re, os, wave, sys
import numpy as np
from scipy import signal
from scipy.signal import fftconvolve
HERE = os.path.dirname(os.path.abspath(__file__)); SR = 48000
src = open(os.path.join(HERE, 'cues.js')).read(); body = re.sub(r'//[^\n]*', '', src[src.index('{'):src.rindex('}') + 1])
C = json.loads(re.sub(r'([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:', r'\1"\2":', body))
N = int(C['dur'] * SR); rng = np.random.default_rng(23)
music = np.zeros((N, 2), np.float32); kb = np.zeros((N, 2), np.float32); sfx = np.zeros((N, 2), np.float32)
vM = np.zeros((N, 2), np.float32); vS = np.zeros((N, 2), np.float32)
def tv(d): return np.arange(int(d * SR)) / SR
def nz(d): return rng.standard_normal(int(d * SR))
def lp(x, f, o=2): b, a = signal.butter(o, min(f, SR / 2 - 100) / (SR / 2), 'low'); return signal.lfilter(b, a, x)
def hp(x, f, o=2): b, a = signal.butter(o, f / (SR / 2), 'high'); return signal.lfilter(b, a, x)
def bp(x, f1, f2, o=2): b, a = signal.butter(o, [f1 / (SR / 2), min(f2, SR / 2 - 100) / (SR / 2)], 'band'); return signal.lfilter(b, a, x)
def lpv(x, fa, seg=512):                     # lowpass with a moving cutoff (block-wise, overlapping history)
    y = np.zeros_like(x)
    for i in range(0, len(x), seg):
        f = float(fa[min(i, len(fa) - 1)]); y[i:i + seg] = lp(x[max(0, i - 2048):i + seg], f)[-len(x[i:i + seg]):]
    return y
def osc(f): return np.sin(2 * np.pi * np.cumsum(f) / SR)
def add(bus, t0, x, g=1., pan=0., rv=0.):
    if x.ndim == 1: x = np.stack([x * np.cos((pan + 1) * np.pi / 4), x * np.sin((pan + 1) * np.pi / 4)], 1) * 1.414
    i = int(round(t0 * SR))
    if i < 0: x = x[-i:]; i = 0
    j = min(N, i + len(x))
    if j <= i: return
    bus[i:j] += (x[:j - i] * g).astype(np.float32)
    if rv: (vM if bus is music else vS)[i:j] += (x[:j - i] * g * rv).astype(np.float32)
def S(t0, x, g=1., pan=0., rv=0.): add(sfx, t0, x, g, pan, rv)
def nf(n):
    m = {'C':0,'C#':1,'Db':1,'D':2,'Eb':3,'E':4,'F':5,'F#':6,'Gb':6,'G':7,'Ab':8,'A':9,'Bb':10,'B':11}
    return 440 * 2 ** ((12 * (int(n[-1]) + 1) + m[n[:-1]] - 69) / 12)
def att(t, a=.002): return np.minimum(1, t / a)

# ================================================= creamy sound-design kit
def thock(t0, g=.5, pan=0., deep=1.):        # lubed, deep mechanical key: round body + soft clack, no hiss
    r = np.random.default_rng(int(t0 * 1e4)); t = tv(.14); f = (165 + 30 * r.random()) * deep
    x = osc(f * (1 + .7 * np.exp(-t / .005))) * np.exp(-t / .024)                  # the "thock" body
    x += .32 * osc(np.full(len(t), f * 3.1)) * np.exp(-t / .010)                    # hollow plastic housing
    x += .30 * lp(bp(r.standard_normal(len(t)), 900, 3000), 3500) * np.exp(-t / .0025)   # soft clack
    x += .35 * lp(r.standard_normal(len(t)), 420) * np.exp(-t / .010)               # bottom-out
    S(t0, lp(x * att(t, .0008), 5000), g * (.85 + .3 * r.random()), pan + (r.random() - .5) * .25, .05)
def plop(t0, g=.4, f0=260, f1=760, pan=0., dec=.06):    # creamy bubble plop: fast upward pitch glide, round decay
    t = tv(dec * 5); k = np.minimum(1, t / .028); f = f0 * (f1 / f0) ** (k ** .6)
    x = osc(f) * np.exp(-t / dec) * att(t, .003) + .35 * osc(f * .5) * np.exp(-t / (dec * .7))
    S(t0, lp(x, 3000), g, pan, .12)
def boop(t0, g=.35, f=520, pan=0., dec=.07):   # soft downward UI pop ("buttery")
    t = tv(dec * 5); x = osc(f * (1 + .9 * np.exp(-t / .006))) * np.exp(-t / dec) * att(t, .002)
    x += .25 * osc(f * 2 * (1 + .9 * np.exp(-t / .006))) * np.exp(-t / (dec * .5)); S(t0, lp(x, 3500), g, pan, .1)
def mag(t0, g=.5, pan=0., f=95):               # magnetic snap: sub thump + mid knock + a whisper of tick
    t = tv(.3); x = osc(f * (1 + .8 * np.exp(-t / .007))) * np.exp(-t / .06)
    x += .55 * osc(np.full(len(t), f * 4.1)) * np.exp(-t / .014)
    x += .18 * lp(bp(nz(.3), 1800, 4500), 5000) * np.exp(-t / .0015)
    S(t0, x * att(t, .0008), g, pan, .1)
def bell(t0, g=.2, f=1320, pan=0., dec=.45):   # soft FM marimba/bell: chimes and confirmations
    t = tv(dec * 4); x = np.sin(2 * np.pi * f * t + 1.1 * np.exp(-t / .02) * np.sin(2 * np.pi * 4 * f * t)) * np.exp(-t / dec)
    x += .3 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t / (dec * .3)); S(t0, x * att(t, .001), g, pan, .35)
def tick(t0, g=.18, f=1650, pan=0.):          # wooden tick (not a bright click)
    t = tv(.06); x = osc(np.full(len(t), f)) * np.exp(-t / .008) + .4 * osc(np.full(len(t), f * 2.3)) * np.exp(-t / .004)
    S(t0, x * att(t, .0005), g, pan)
def whoosh(t0, d=.4, g=.3, f0=250, f1=1800, p0=-.6, p1=.6, peak=.6, tone=.35):  # tight, rounded air + a tonal glide
    t = tv(d); x = nz(d); y = np.zeros_like(x); seg = 384
    for i in range(0, len(x), seg):
        fc = f0 * (f1 / f0) ** (i / len(x)); y[i:i + seg] = bp(x[max(0, i - 1024):i + seg], fc / 1.6, min(fc * 1.6, 9000))[-len(x[i:i + seg]):]
    y = lp(y, 3200) * 2.2 + tone * osc(np.geomspace(f0 / 2, f1 / 2, len(t)))
    e = np.where(t / d < peak, (t / d / peak) ** 2.4, ((1 - t / d) / (1 - peak)) ** 1.6); pn = np.linspace(p0, p1, len(t))
    add(sfx, t0, np.stack([y * e * np.cos((pn + 1) * np.pi / 4), y * e * np.sin((pn + 1) * np.pi / 4)], 1) * 1.41, g, 0, .15)
def suck(t0, t1, g=.45):                       # reverse suction: swells and stops dead on the cut
    d = t1 - t0; t = tv(d); u = t / d
    x = lp(hp(nz(d), 300), 2600) * u ** 4 * 2.2 + .6 * osc(90 * 5 ** u) * u ** 3 + .4 * osc(45 * 5 ** u) * u ** 2
    x[-int(.006 * SR):] *= np.linspace(1, 0, int(.006 * SR)); S(t0, x, g)
def impact(t0, g=.8, f0=72, f1=34, dec=.45, body=1.):    # deep, clean hit: sub + chest thump + dark burst
    t = tv(dec * 4); x = osc(f1 + (f0 - f1) * np.exp(-t / .05)) * np.exp(-t / dec)
    x += body * .7 * osc(np.full(len(t), 140.)) * np.exp(-t / .05) + body * .5 * lp(nz(dec * 4), 900) * np.exp(-t / .03)
    S(t0, x * att(t, .0015), g, 0, .18)
def glide(t0, d, g=.12, f0=300, f1=1200, pan=0.):        # smooth tonal rise (line drawing / sheen)
    t = tv(d); f = np.geomspace(f0, f1, len(t)) * (1 + .006 * np.sin(2 * np.pi * 6 * t))
    e = np.sin(np.pi * np.minimum(1, t / d)) ** 1.5; S(t0, (osc(f) + .3 * osc(f * 2)) * e, g, pan, .4)
def swipe(t0, d=.22, g=.25, f0=500, f1=1400, pan=0.):    # creamy selection swipe: filtered, soft-edged
    t = tv(d); y = lp(bp(nz(d), f0, f1 * 1.5), 2500) * np.sin(np.pi * t / d) ** 2
    S(t0, y * 2.5 + .25 * osc(np.geomspace(f0, f1, len(t))) * np.sin(np.pi * t / d) ** 2, g, pan, .1)
def roll(t0, t1, n, g=.12, f=1500, pan=0.):               # decelerating counter ticks (numbers rolling to their value)
    for i in range(n): u = (i / (n - 1)) ** 1.8; tick(t0 + (t1 - t0) * u, g * (1 - .4 * u), f + 40 * i, pan)
def sonic_logo(t0):                                       # one deep, very clean hit + a resolving chord
    impact(t0, 1.0, 78, 32, .7, 1.2); mag(t0 + .01, .5, 0, 70)
    t = tv(4.0)
    for i, n in enumerate(['D3', 'A3', 'E4', 'F#4', 'A4', 'D5']):
        f = nf(n); x = (np.sin(2 * np.pi * f * t) + .2 * np.sin(2 * np.pi * 2 * f * t)) * np.exp(-t / 1.6) * att(t, .015 + .025 * i)
        S(t0 + .025 * i, x, .055, -.5 + .2 * i, .6)
    bell(t0 + .05, .12, nf('A5'), 0, .9)

# ================================================= score: 120 BPM, D major / B minor, original
B = .5                                  # one beat
BAR = 4 * B
CH = [(['B2', 'D3', 'F#3', 'A3'], 'B1'), (['G2', 'B2', 'D3', 'F#3'], 'G1'), (['D3', 'F#3', 'A3', 'E4'], 'D2'), (['A2', 'C#3', 'E3', 'B3'], 'A1')]
def chord(t): return CH[int(t // BAR) % 4]
def beats(a, b, step=1.):
    k = int(np.ceil(a / (B * step) - 1e-6)); out = []
    while k * B * step < b - 1e-6: out.append(round(k * B * step, 4)); k += 1
    return out
KICKS = []
def kick(t0, g=.6):
    t = tv(.5); x = osc(46 + 110 * np.exp(-t / .028)) * np.exp(-t / .22) + .12 * lp(bp(nz(.5), 1500, 5000), 6000) * np.exp(-t / .002)
    add(kb, t0, x * att(t, .001), g); KICKS.append(t0)
def clap(t0, g=.16):
    t = tv(.4); x = np.zeros_like(t)
    for d in (0, .008, .017): x += np.roll(bp(nz(.4), 900, 3500) * np.exp(-t / .009), int(d * SR))
    add(music, t0, lp(x + .5 * bp(nz(.4), 900, 3800) * np.exp(-t / .09), 6000), g, -.05, .3)
def hat(t0, g=.03, pan=.3, dec=.02): add(music, t0, lp(hp(nz(.25), 7000), 12000) * np.exp(-tv(.25) / dec), g, pan)
def snare(t0, g=.12):
    t = tv(.25); x = .6 * osc(np.full(len(t), 190.)) * np.exp(-t / .03) + lp(bp(nz(.25), 1200, 6000), 7000) * np.exp(-t / .05)
    add(music, t0, x, g, .1, .2)
def bass(t0, d, n, g=.26):
    f = nf(n); t = tv(d + .05); x = np.sin(2 * np.pi * f * t) + .45 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t / .12) + .2 * signal.sawtooth(2 * np.pi * f * t)
    x *= att(t, .004) * np.clip((d + .04 - t) / .04, 0, 1); add(music, t0, lp(x, 700), g)
def pluck(t0, n, g=.07, pan=0., dec=.25):
    f = nf(n); t = tv(1.2); x = np.sin(2 * np.pi * f * t + 1.3 * np.exp(-t / .035) * np.sin(2 * np.pi * 2 * f * t)) * np.exp(-t / dec)
    add(music, t0, x * att(t), g, pan, .4)
def pad(t0, t1, notes, g=.05, cut=1200, a=.6, rel=.8):
    d = t1 - t0 + rel; t = tv(d); L = np.zeros_like(t); R = np.zeros_like(t)
    for n in notes:
        f = nf(n); L += signal.sawtooth(2 * np.pi * f * .996 * t + rng.random() * 6); R += signal.sawtooth(2 * np.pi * f * 1.004 * t + rng.random() * 6)
    e = np.minimum(1, t / a) * np.where(t > t1 - t0, np.exp(-(t - (t1 - t0)) / (rel / 3)), 1)
    add(music, t0, np.stack([lp(L, cut), lp(R, cut)], 1) * e[:, None] / len(notes), g, 0, .3)
def stab(t0, notes, g=.06, pan=0.):
    t = tv(.35); x = sum(signal.sawtooth(2 * np.pi * nf(n) * t) for n in notes) / len(notes)
    add(music, t0, lp(x, 2600) * np.exp(-t / .08) * att(t, .003), g, pan, .3)
def sub_drone(t0, t1, n='D1', g=.12):
    d = t1 - t0; t = tv(d); x = np.sin(2 * np.pi * nf(n) * t) * np.minimum(1, t / .3) * np.minimum(1, (d - t) / .05); add(music, t0, x, g)
def m_riser(t0, t1, g=.1):
    d = t1 - t0; t = tv(d); u = t / d
    x = lpv(signal.sawtooth(2 * np.pi * np.cumsum(110 * 4 ** u) / SR), 400 + 3000 * u ** 2) * u ** 2 + .35 * lpv(hp(nz(d), 500), 1500 + 3500 * u) * u ** 3
    add(music, t0, x, g, 0, .2)
ARP = ['F#4', 'A4', 'B4', 'D5', 'E5', 'D5', 'B4', 'A4']
def bar_pad(a, b, g=.04, cut=1300):
    for t0 in beats(a, b, 4):
        notes, _ = chord(t0); pad(max(a, t0), min(b, t0 + BAR) - .02, notes, g, cut, .25, .35)

# --- S1 hook 0 → 3.0: a heartbeat sub pulse, two smashes, a suction
sub_drone(0, 1.17, 'D1', .16)
for t0 in beats(0, 1.1, .5): kick(t0, .16 + .14 * t0)                  # 8th-note heartbeat that grows into the smash
pad(1.25, 2.5, ['B2', 'D3', 'F#3', 'A3'], .05, 900, .05, .3)
for t0 in beats(1.75, 2.55): kick(t0, .38); hat(t0 + .25, .02)
m_riser(1.9, 2.98, .08)
# --- S2 reveal 3.0 → 8.0: swell, half-time kick, then the groove arrives on MEET CURSOR.
pad(3.0, 4.5, ['D2', 'A2', 'D3', 'E3', 'A3'], .065, 800, .8, .5)
for t0 in beats(4.5, 6.5, 2): kick(t0, .42); bass(t0, .9, chord(t0)[1], .2)
for t0 in beats(4.5, 6.5): hat(t0 + .25, .016)
bar_pad(4.5, 6.45, .04, 1000)
for t0 in beats(6.5, 8.0):
    k = round(t0 / B); kick(t0, .5); hat(t0 + .25, .024)
    if k % 2: clap(t0, .12)
    bass(t0, .22, chord(t0)[1], .22); bass(t0 + .25, .18, chord(t0)[1][:-1] + str(int(chord(t0)[1][-1]) + 1), .14)
bar_pad(6.5, 8.0, .04, 1500)
# --- S3 tab 8.0 → 15.0: groove; a hard silence before the Tab press, then it drops
def groove(a, b, kg=.5, cl=.13, hg=.024, bg=.24, arp=.0, sixteen=False, oct_up=False, pg=.04, pc=1500):
    for t0 in beats(a, b):
        k = round(t0 / B); n = chord(t0)[1]; kick(t0, kg)
        if k % 2: clap(t0, cl)
        if sixteen:
            for s in range(4): hat(t0 + s * B / 4, hg if s % 2 == 0 else hg * .6)
        else: hat(t0 + B / 2, hg)
        bass(t0, .2, n, bg); bass(t0 + .25, .17, n[:-1] + str(int(n[-1]) + 1), bg * .6)
        if arp:
            for s in (0, 1):
                a_n = ARP[(2 * k + s) % 8]
                if oct_up: a_n = a_n[:-1] + str(int(a_n[-1]) + 1)
                pluck(t0 + s * B / 2, a_n, arp, -.35 + .7 * ((2 * k + s) % 5) / 4)
    bar_pad(a, b, pg, pc)
groove(8.0, 10.0, .42, .1, .02, .2, arp=.03)
for t0 in beats(10.0, 10.18, .5): hat(t0, .02)
groove(10.3, 14.5, .55, .15, .026, .26, arp=.04, sixteen=True)
for i, t0 in enumerate(beats(14.5, 15.0, .25)): snare(t0, .05 + .02 * i)   # fill into the agent
# --- S4 agent 15.0 → 23.0: breathe under the prompt, then drive
pad(15.0, 15.95, ['B2', 'D3', 'F#3', 'B3'], .05, 700, .1, .3)
for t0 in beats(15.0, 15.95, .5): hat(t0, .012)
m_riser(15.2, 15.95, .07)
groove(16.0, 22.9, .58, .15, .03, .27, arp=.035, sixteen=True, pg=.035, pc=1800)
for c in ['d1', 'd2', 'd3', 'd4', 'a1', 'a2', 'a3']: stab(C[c], chord(C[c])[0], .07, .2)   # rhythmic agent accents
m_riser(21.75, 22.9, .09)
# --- S5 hero 23.0 → 32.0: half-time weight on the explosion, then the strongest groove
pad(23.0, 24.5, ['B1', 'F#2', 'B2', 'D3', 'F#3'], .07, 900, .05, .4)
for t0 in (23.0, 24.0): kick(t0, .62); bass(t0, .9, 'B1', .26)
for t0 in beats(23.0, 24.5): hat(t0 + .25, .02)
groove(24.5, 28.5, .62, .17, .032, .29, arp=.045, sixteen=True, oct_up=True, pg=.045, pc=2400)
groove(28.5, 32.0, .55, .15, .026, .25, arp=.035, sixteen=True, pg=.04, pc=1600)
# --- S6 montage 32.0 → 35.95: crescendo (roll accelerates, pitch rises), then a hard cut to silence
for t0 in beats(32.0, 35.95):
    kick(t0, .6 + .05 * (t0 - 32)); bass(t0, .22, chord(t0)[1], .27)
    if round(t0 / B) % 2: clap(t0, .16)
    for s in range(4): hat(t0 + s * B / 4, .03 if s % 2 == 0 else .02)
for t0, step in [(32.0, .5), (33.0, .25), (34.0, .125), (35.0, .0625)]:
    for x in [t0 + i * step for i in range(int(round(1 / step)))]:
        if x < 35.93: snare(x, .04 + .05 * (x - 32) / 4)
m_riser(33.5, 35.95, .14)
pad(32.0, 35.9, ['D3', 'F#3', 'A3', 'E4'], .045, 2600, .1, .05)
# --- S7: silence 35.95 → 36.45, then the sonic logo carries the end

# ================================================= sound design, cue by cue
# S1 hook
plop(C['sh1'] + .04, .3, 200, 520, .3)                                   # keycaps rise
thock(C['cmdk'], .85, .25, .8); thock(C['cmdk'] + .03, .85, .45, .85)       # ⌘ then K: deep, creamy
boop(C['cmdk'] + .07, .25, 620, .3)
whoosh(C['sh2'] - .08, .3, .3, 300, 1600, -.7, .3, .6)
for li in range(8): mag(C['lock0'] + li * .035, .32 - .015 * li, -.5 + li * .14, 110 + 8 * li)   # code fragments lock in
plop(C['lock0'] + .3, .3, 300, 900, 0, .05)
suck(C['push'] - .15, C['sh3'], .55)
impact(C['sh3'], 1.0, 80, 34, .4); thock(C['sh3'], .6, 0, .6)               # IDEAS.
impact(C['sh4'], .95, 70, 32, .45); mag(C['sh4'], .5, 0, 80)               # INTO REALITY.
suck(C['suck'], C['sh5'], .6)
# S2 reveal
impact(C['sh5'], .8, 64, 30, .5, .6); whoosh(C['sh5'], .7, .2, 200, 900, .2, -.2, .3)
bell(C['accent'], .22, nf('A5'), 0, .7); bell(C['accent'] + .02, .14, nf('D5'), -.2, .9); mag(C['accent'], .45, 0, 70)   # logo accent
glide(C['sheen'], .7, .07, 700, 2200, .3)                                 # sheen: tonal, not hiss
whoosh(C['sh6'] - .05, .55, .3, 220, 1300, -.8, .6, .45)
for i, c in enumerate(['snap1', 'snap2', 'snap3', 'snap4']):
    p = [-.6, .6, -.3, .3][i]; mag(C[c], .55, p, 100 + 12 * i); plop(C[c] + .01, .22, 300 + 40 * i, 820 + 80 * i, p, .045)
plop(C['icon'], .3, 380, 1100, 0, .05); bell(C['icon'] + .02, .1, nf('E6'), 0, .3)
whoosh(C['sh7'] - .1, .38, .28, 1600, 300, .3, -.3, .5)
impact(C['meet'], .85, 70, 34, .4); thock(C['meet'] + .01, .5, 0, .7)        # MEET CURSOR.
# S3 tab
whoosh(C['sh8'] - .12, .4, .25, 900, 250, .5, -.2, .4)
for t0 in C['T1']: thock(t0, .42, .15)
whoosh(C['sh9'] - .06, .2, .16, 600, 1800, -.3, .3, .5)
glide(C['ghost'], .6, .08, 520, 880, .25); plop(C['ghost'] + .05, .18, 240, 560, .25, .05)   # ghost suggestion appears
plop(C['sh10'] + .02, .25, 200, 480, -.3, .05)
thock(C['tab'], 1.0, 0, .62); mag(C['tab'] + .005, .65, 0, 76); plop(C['tab'] + .03, .4, 260, 880, 0, .07)   # THE Tab
impact(C['tab'] + .01, .45, 60, 34, .25, .3); bell(C['tab'] + .07, .1, nf('F#5'), .2, .5)
whoosh(C['sh11'] - .06, .3, .22, 300, 1400, -.5, .5, .5)
for i in range(6): plop(C['lift'] + .06 * i, .2, 220 + 30 * i, 520 + 70 * i, -.5 + .2 * i, .045)   # slabs lift
for i in range(6): mag(C['back'] + .2 + .03 * i, .3, .5 - .2 * i, 120 + 10 * i)                   # slabs snap home
swipe(C['select'], .22, .35, 450, 1300, .1); tick(C['select'] + .22, .14, 1500, .3)
whoosh(C['sh12'] - .08, .22, .2, 1500, 400, .2, -.3, .5)
for t0 in C['TL']: thock(t0, .5, -.1, .9)
for i in range(14): boop(C['more'] + i * .028 + .2, .2, 420 + 22 * i, -.6 + i * .09, .05)       # MORE BUILDING. letters snap
mag(C['more'] + .58, .45, 0, 85)
# S4 agent
whoosh(C['sh13'] - .1, .4, .25, 250, 1200, -.4, .4, .5)
for t0 in C['TP']: thock(t0, .36, .35)
thock(C['send'], .9, .35, .7); plop(C['send'] + .02, .45, 280, 1000, .35, .07); whoosh(C['send'] + .05, .3, .2, 500, 1800, .4, .1, .5)
whoosh(C['fan'] - .05, .45, .3, 250, 1400, -.8, .5, .5)
for i in range(4): mag(C['fan'] + i * .08 + .24, .4, -.6 + .4 * i, 105 + 10 * i)
for i, c in enumerate(['d1', 'd2', 'd3', 'd4']):
    p = .3 - .2 * i; whoosh(C[c] - .05, .25, .18, 1400, 400, .6, 0, .45); mag(C[c] + .22, .5, p, 98 + 6 * i)
    for j in range(5): tick(C[c] + .2 + j * .035, .07, 1350 + 90 * j, p)                    # diff lines slide in
    plop(C[c] + .38, .14, 340, 900, p, .04)
whoosh(C['sh16'] - .06, .3, .2, 300, 1500, -.8, -.2, .5); whoosh(C['sh16'] - .04, .3, .2, 300, 1500, .8, .2, .5)
for t0 in C['TC']: thock(t0, .4, -.45)
for i in range(6): tc = C['sh16'] + .18 + i * .17; tick(tc, .16, 1500 + 60 * i, .45); boop(tc + .01, .14, 560 + 40 * i, .45, .04)
bell(C['ready'], .16, nf('A5'), -.3, .5); bell(C['ready'] + .08, .12, nf('D6'), -.3, .6)
whoosh(C['sh17'] - .06, .3, .2, 400, 1400, -.4, .4, .5)
for a, n in [('a1', 4), ('a2', 1), ('a3', 1)]:
    whoosh(C[a] - .03, .26, .18, 300, 1800, -.6, .6, .7, .5)                                # line lifts off and flies
    for j in range(n): plop(C[a] + .2 + j * .05, .32, 260 + 50 * j, 820 + 60 * j, .5, .055)  # lands as a component
    mag(C[a] + .2, .35, .5, 110)
impact(C['onep'], .6, 66, 36, .3, .5); impact(C['endless'], .5, 60, 34, .3, .4)
suck(22.45, C['sh19'], .6)
# S5 hero: explode, reconstruct, data comes alive
impact(C['sh19'], 1.0, 72, 30, .55); whoosh(C['sh19'] + .02, .9, .32, 1500, 220, 0, 0, .15)
for i in range(7): plop(C['sh19'] + .05 + i * .07, .16, 500 - 30 * i, 260 - 10 * i, -.6 + .2 * i, .06)   # layers separate
whoosh(C['sh20'] - .1, .35, .2, 250, 1200, .4, -.4, .5)
for i in range(7):
    ts = C['r0'] + i * C['rStep'] + .2; p = [-.5, -.6, -.2, .2, .6, -.3, .4][i]
    mag(ts, .6, p, 88 + 9 * i); plop(ts + .01, .24, 240 + 30 * i, 700 + 70 * i, p, .05)          # each part snaps home
    if 1 <= i <= 4: roll(ts + .03, ts + .6, 9, .07, 1500 + 80 * i, p)                            # its number rolls up
glide(C['r0'] + 5 * C['rStep'] + .2, 1.15, .08, 330, 990, -.1)                                     # revenue line draws
for i in range(5): plop(C['r0'] + 6 * C['rStep'] + .2 + i * .08 + .1, .22, 260 + 40 * i, 760 + 70 * i, -.4 + .2 * i, .05)   # bars grow
whoosh(C['flat'] - .05, .8, .18, 300, 900, -.2, .2, .4)
plop(C['hover'], .32, 300, 900, .2, .05); boop(C['hover'] + .06, .16, 760, .2)
thock(C['export'], .8, .4, .75); boop(C['export'] + .03, .2, 680, .4)
whoosh(C['sh21'] - .05, 1.1, .3, 1300, 200, .2, -.2, .3)
mag(C['sh21'] + 1.1, .4, 0, 80)                                                                   # lands inside the editor
impact(C['fromc'], .6, 66, 34, .3, .5); impact(C['toc'], .6, 60, 32, .32, .5); bell(C['toc'] + .02, .08, nf('A5'), .2, .6)
# S6 montage: every cut hits
for c in ['m1', 'm2', 'm3', 'm4']: impact(C[c], .55, 70, 34, .22, .6); whoosh(C[c] - .1, .14, .2, 2000, 500, .5, -.5, .4)
thock(C['m1'] + .1, .85, 0, .65); mag(C['m1'] + .1, .5, 0, 80)                                   # Tab again
mag(C['m2'] + .13, .5, -.3, 100); [tick(C['m2'] + .13 + j * .035, .06, 1400 + 80 * j) for j in range(5)]
impact(C['m3'] + .02, .5, 60, 30, .3); [plop(C['m3'] + .05 + i * .06, .13, 480 - 30 * i, 250, -.5 + .2 * i, .05) for i in range(5)]
plop(C['m4'] + .12, .35, 280, 900, .4, .05); mag(C['m4'] + .12, .4, .4, 105)
suck(C['m5'], C['black'], .7); mag(C['m5'], .4, 0, 80)
# S7 lockup
sonic_logo(C['sh23'])
mag(C['tag'], .3, 0, 90); boop(C['tag'] + .02, .12, 640)
tick(C['url'], .1, 1700)

# ================================================= mix
def room(x, dec=.32, length=1.4, seed=5):
    r = np.random.default_rng(seed); t = tv(length); ir = r.standard_normal(len(t)) * np.exp(-t / dec); ir = lp(ir, 5000); ir /= np.sqrt((ir ** 2).sum())
    return np.stack([fftconvolve(x[:, c], np.roll(ir, 17 * c), 'full')[:N] for c in (0, 1)], 1).astype(np.float32)
# sidechain pump: the music ducks under every kick, which gives the score its pulse
duck = np.ones(N, np.float32); dt = tv(.3); dcurve = (1 - .45 * np.exp(-dt / .07)).astype(np.float32)
for k in KICKS:
    i = int(k * SR) + 30; j = min(N, i + len(dcurve))
    if j > i: duck[i:j] = np.minimum(duck[i:j], dcurve[:j - i])
music_out = (music + room(vM, .45, 1.8) * .35) * .48
music_out *= duck[:, None] ** .6
music_out += kb * .48                    # kicks sit outside the duck
sfx_out = (sfx + room(vS, .25, 1.0, 9) * .3) * 1.3
# silence moments (music only; the SFX that live in them stay): before IDEAS., before Tab, before the explosion,
# and the full blackout before the logo (SFX too)
def gate(x, a, b, fade=.03):
    g = np.ones(N, np.float32); i, j, f = int(a * SR), int(b * SR), int(fade * SR)
    g[i:j] = 0; g[max(0, i - f):i] = np.linspace(1, 0, min(f, i)); x *= g[:, None]
gate(music_out, 1.17, 1.25, .02); gate(music_out, 10.18, 10.3, .02); gate(music_out, 22.9, 23.0, .02)
gate(music_out, C['black'], C['sh23'] + .1, .01)
g = np.ones(N, np.float32); i, j = int(C['black'] * SR), int(C['sh23'] * SR); g[i:j] = 0; g[i:i + int(.01 * SR)] = np.linspace(1, 0, int(.01 * SR)); sfx_out *= g[:, None]
def rms(x): return float(np.sqrt(np.mean(x ** 2)) + 1e-9)
def ww(name, x):
    y = np.clip(x, -1, 1); w = wave.open(os.path.join(HERE, 'build', name), 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((y * 32767).astype(np.int16).tobytes()); w.close()
os.makedirs(os.path.join(HERE, 'build'), exist_ok=True)
fo = int(.3 * SR)
for x in (music_out, sfx_out): x[-fo:] *= np.linspace(1, 0, fo)[:, None]
def limiter_gain(x, thr=.89, look=.003, rel=.09):
    # clean look-ahead peak limiter: a smooth gain curve (no waveshaping, no saturation)
    L = int(look * SR); m = np.abs(x).max(1); req = np.minimum(1, thr / (m + 1e-9))
    req = np.pad(req, (0, L), constant_values=1); req = np.lib.stride_tricks.sliding_window_view(req, L + 1).min(1)[:len(m)]   # look ahead
    g = np.empty_like(req); a = np.exp(-1 / (L / 2 + 1)); r = np.exp(-1 / (rel * SR)); cur = 1.0
    for i in range(len(req)):
        tgt = req[i]; cur = a * cur + (1 - a) * tgt if tgt < cur else r * cur + (1 - r) * tgt; g[i] = cur
    return np.minimum(g, req).astype(np.float32)
mix = music_out + sfx_out; pre = 10 ** (-15.5 / 20) / rms(mix[:int(C['black'] * SR)])        # bring the body up, then catch the peaks
music_out *= pre; sfx_out *= pre; gl = limiter_gain(music_out + sfx_out)
music_out *= gl[:, None]; sfx_out *= gl[:, None]
print('pre gain', round(pre, 2), 'max GR dB', round(20 * np.log10(gl.min()), 1), 'frames >3dB GR', int((gl < .708).sum()))
ww('music.wav', music_out); ww('sfx.wav', sfx_out); ww('mix_raw.wav', music_out + sfx_out)
sp = float(np.abs(sfx_out).max()); ww('nomusic_raw.wav', sfx_out * (.89 / sp))
def rms(x): return float(np.sqrt(np.mean(x ** 2)) + 1e-9)
if '--report' in sys.argv:
    db = lambda x: 20 * np.log10(rms(x))
    for t0 in np.arange(0, 40, 2.0):
        i, j = int(t0 * SR), int((t0 + 2) * SR); print(f'{t0:5.1f}  music {db(music_out[i:j]):6.1f}  sfx {db(sfx_out[i:j]):6.1f}')
mx = np.abs(music_out + sfx_out).max(1); pk_t = sorted(range(0, N, SR // 10), key=lambda i: -mx[i:i + SR // 10].max())[:8]
print('top peaks', [(round(i / SR, 1), round(float(mx[i:i + SR // 10].max()), 2)) for i in pk_t])
