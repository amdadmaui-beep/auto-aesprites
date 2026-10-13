# AVE promo V2 — voice, sound design and music, all placed from cues.js.
# If build/music.wav exists (the supplied track) it replaces the placeholder score.
import json, re, os, subprocess, sys, wave
import numpy as np
from scipy import signal

ROOT = os.path.dirname(os.path.abspath(__file__))
VO = os.path.join(ROOT, '..', 'vo2')
CLIPA = os.path.join(ROOT, 'clips', 'audio')
SR = 48000
src = open(os.path.join(ROOT, 'cues.js')).read()
body = re.sub(r'//[^\n]*', '', src[src.index('{'):src.rindex('}') + 1])
body = re.sub(r'([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:', r'\1"\2":', body)
C = json.loads(body)
DUR = C['dur']; N = int(DUR * SR)
rng = np.random.default_rng(11)
def buf(): return np.zeros((N, 2), np.float32)
music, sfx, vox, clipbus = buf(), buf(), buf(), buf()
def tv(d): return np.arange(int(d * SR)) / SR
def add(bus, t0, x, gain=1.0, pan=0.0):
    if x.ndim == 1:
        l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        x = np.stack([x * l * 1.414, x * r * 1.414], 1)
    i = int(round(t0 * SR))
    if i < 0: x = x[-i:]; i = 0
    j = min(N, i + len(x))
    if j > i: bus[i:j] += (x[:j - i] * gain).astype(np.float32)
def lp(x, f, o=2): b, a = signal.butter(o, min(f, SR / 2 - 100) / (SR / 2), 'low'); return signal.lfilter(b, a, x)
def hp(x, f, o=2): b, a = signal.butter(o, f / (SR / 2), 'high'); return signal.lfilter(b, a, x)
def bp(x, f1, f2, o=2): b, a = signal.butter(o, [f1 / (SR / 2), min(f2, SR / 2 - 100) / (SR / 2)], 'band'); return signal.lfilter(b, a, x)
def noise(d): return rng.standard_normal(int(d * SR))
def nf(n):
    names = {'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8, 'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11}
    return 440 * 2 ** ((12 * (int(n[-1]) + 1) + names[n[:-1]] - 69) / 12)

# ------------------------------------------------------------ instruments
def kick(t0, g=.5, bus=None):
    t = tv(.45); f = 48 + 90 * np.exp(-t / .028); x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / .19)
    x += .35 * hp(noise(.45), 2500) * np.exp(-t / .003); add(music if bus is None else bus, t0, np.tanh(x * 1.6), g)
def clap(t0, g=.13):
    t = tv(.35); x = np.zeros_like(t)
    for d in (0, .009, .018): x += np.roll(bp(noise(.35), 900, 4200) * np.exp(-t / .012), int(d * SR))
    x += .6 * bp(noise(.35), 1200, 6000) * np.exp(-t / .09); add(music, t0, x, g, -.05)
def hat(t0, g=.03, pan=.25, dec=.028, op=False):
    x = hp(noise(.4), 7500) * np.exp(-tv(.4) / (.16 if op else dec)); add(music, t0, x, g, pan)
def tickp(t0, g=.03, f=5200, pan=0):  # glitch click percussion
    t = tv(.03); x = np.sign(np.sin(2 * np.pi * f * t)) * np.exp(-t / .004); add(music, t0, x, g, pan)
def pluck(t0, n, g=.08, pan=0., dec=.28, bright=1.):
    f = nf(n); t = tv(1.2)
    x = np.sin(2 * np.pi * f * t + 1.2 * np.sin(2 * np.pi * f * 2 * t) * np.exp(-t / .05))
    x += .25 * bright * np.sin(2 * np.pi * 3 * f * t) * np.exp(-t / .04)
    x *= np.minimum(1, t / .002) * np.exp(-t / dec); add(music, t0, lp(x, 7000), g, pan)
def bass(t0, d, n, g=.16, slide=0.0):
    f = nf(n); t = tv(d); ff = f * (1 + slide * np.exp(-t / .05))
    x = np.sin(2 * np.pi * np.cumsum(ff) / SR); x = np.tanh(2.2 * x) * .7 + .3 * np.sin(2 * np.pi * np.cumsum(ff * 2) / SR) * np.exp(-t / .08)
    e = np.minimum(1, t / .004) * np.minimum(1, np.maximum(0, d - t) / .03) * np.exp(-t / (d * 1.5))
    add(music, t0, lp(x * e, 900), g)
def pad(t0, t1, notes, g=.05, cut=1600, att=.3, rel=.6, pump=True):
    d = t1 - t0 + rel; t = tv(d); L = np.zeros_like(t); R = np.zeros_like(t)
    for n in notes:
        f = nf(n)
        for k, det in enumerate((-.12, .0, .13)):
            w = signal.sawtooth(2 * np.pi * f * (1 + det / 100 * 3) * t + rng.random() * 6)
            (L if k == 0 else R if k == 2 else L)[:] += w * (1 if k != 1 else .5)
            if k == 1: R[:] += w * .5
    e = np.minimum(1, t / att) * np.where(t > t1 - t0, np.exp(-(t - (t1 - t0)) / (rel / 3)), 1)
    if pump:  # sidechain feel on quarter notes
        ph = ((t0 + t) % .5) / .5; e = e * (.55 + .45 * np.minimum(1, ph / .35))
    x = np.stack([lp(L, cut), lp(R, cut)], 1) * e[:, None] / (len(notes) * 2); add(music, t0, x, g)

# ------------------------------------------------------------ sfx
def whoosh(t0, d=.4, g=.2, f1=400, f2=4000, p0=-.5, p1=.5, peak=.6):
    t = tv(d); x = noise(d); y = np.zeros_like(x); seg = 256
    for i in range(0, len(x), seg):
        fc = f1 * (f2 / f1) ** (i / len(x)); y[i:i + seg] = bp(x[max(0, i - 512):i + seg], fc * .6, fc * 1.6)[-len(x[i:i + seg]):]
    e = np.where(t / d < peak, (t / d / peak) ** 2, ((1 - t / d) / (1 - peak)) ** 1.5); pn = np.linspace(p0, p1, len(t))
    add(sfx, t0, np.stack([y * e * np.cos((pn + 1) * np.pi / 4), y * e * np.sin((pn + 1) * np.pi / 4)], 1) * 1.4, g)
def click(t0, g=.25, f=2600, pan=0.):
    t = tv(.06); x = bp(noise(.06), f * .7, f * 1.5) * np.exp(-t / .005) + .4 * np.sin(2 * np.pi * f * .5 * t) * np.exp(-t / .01); add(sfx, t0, x, g, pan)
def tick(t0, g=.06, pan=0.): click(t0, g, 4300, pan)
def tone(t0, f, g=.1, pan=0., dec=.06):
    t = tv(.3); x = np.sin(2 * np.pi * f * t) * np.exp(-t / dec) + .4 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t / (dec / 3)) + .3 * hp(noise(.3), 3000) * np.exp(-t / .003)
    add(sfx, t0, x, g, pan)
def thump(t0, g=.3, f0=120, f1=55, dec=.11):
    t = tv(.4); f = f1 + (f0 - f1) * np.exp(-t / .03); x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / dec) + .2 * lp(noise(.4), 700) * np.exp(-t / .02); add(sfx, t0, x, g)
def mask(t0, g=.06, pan=0.):  # soft "thup" for mask reveals
    t = tv(.12); x = lp(noise(.12), 1800) * np.exp(-t / .025) + .5 * np.sin(2 * np.pi * 180 * t) * np.exp(-t / .03); add(sfx, t0, x, g, pan)
def cloth(t0, d=.35, g=.08, pan=.3):
    t = tv(d); x = bp(noise(d), 600, 3200) * np.sin(np.pi * t / d) ** 2 * (.6 + .4 * np.abs(np.sin(t * 60))); add(sfx, t0, x, g, pan)
def slide(t0, g=.2, d=.24, pan=-.3):
    t = tv(d); x = bp(noise(d), 1500, 6500) * np.sin(np.pi * t / d) ** 1.5; add(sfx, t0, x, g, pan); thump(t0 + d * .85, g * .45, 190, 95, .05)
def chime(t0, fs, g=.22, step=.05, dec=.8):
    for k, f in enumerate(fs):
        t = tv(dec * 3); x = np.sin(2 * np.pi * f * t + 1.1 * np.sin(2 * np.pi * f * 3.5 * t) * np.exp(-t / .18)) * np.exp(-t / dec)
        add(sfx, t0 + k * step, x, g / len(fs) * 1.6, (k - len(fs) / 2) * .2)
def riser(t0, t1, g=.12):
    d = t1 - t0; t = tv(d); z = noise(d); y = np.zeros_like(t); seg = 512
    for i in range(0, len(t), seg):
        fc = 500 * (14 ** (i / len(t))); y[i:i + seg] = bp(z[max(0, i - 1024):i + seg], fc * .7, fc * 1.4)[-len(z[i:i + seg]):]
    tone_ = .4 * np.sin(2 * np.pi * np.cumsum(220 * 4 ** (t / d)) / SR)
    add(sfx, t0, (y + tone_) * (t / d) ** 2.4, g)
def scrub(t0, t1, g=.08):
    t = t0
    while t < t1:
        p = (t - t0) / (t1 - t0); sp = np.sin(np.pi * p); click(t, g * (.4 + .6 * sp), 1700 + 1700 * sp, -.3 + .6 * p); t += .045 - .026 * sp
def pulse(t0, g=.18):
    t = tv(.7); x = np.sin(2 * np.pi * 70 * t) * np.exp(-t / .25) * (1 + .5 * np.sin(2 * np.pi * 9 * t)); add(sfx, t0, lp(x, 400), g)
def hit(t0, g=.5):
    t = tv(2.0); f = 41.2 * (1 + 1.3 * np.exp(-t / .055)); x = np.tanh(2.0 * np.sin(2 * np.pi * np.cumsum(f) / SR)) * np.exp(-t / .5)
    x += .55 * lp(noise(2.0), 1600) * np.exp(-t / .045) + .3 * hp(noise(2.0), 4000) * np.exp(-t / .012); add(sfx, t0, x, g)
def swell(t0, t1, g=.18):
    d = t1 - t0; t = tv(d); add(sfx, t0, lp(noise(d), 2400) * (t / d) ** 3 + .3 * np.sin(2 * np.pi * 82.4 * t) * (t / d) ** 2, g)

# ------------------------------------------------------------ placeholder score (Apple-style minimal tech-pop, 120 BPM, F major)
motif = [(0, 'C5'), (.25, 'D5'), (.5, 'F5'), (1.0, 'D5'), (1.25, 'C5'), (1.5, 'A4'), (1.75, 'C5')]  # 2s phrase
chords = {0: ['F3', 'A3', 'C4', 'E4'], 2: ['D3', 'F3', 'A3', 'C4'], 4: ['A#2', 'D3', 'F3', 'A3', 'C4'], 6: ['C3', 'E3', 'G3', 'D4']}
roots = {0: 'F1', 2: 'D2', 4: 'A#1', 6: 'C2'}
def ch(t): return chords[int(t % 8 // 2 * 2)]
def rt(t): return roots[int(t % 8 // 2 * 2)]
def section(t0, t1, kickpat, claps, hats, bassOn, motifG, padG, glitch=False):
    b = t0
    while b < t1 - 1e-6:
        bar = b
        if padG: pad(bar, min(bar + 2, t1), ch(bar), padG, 1800)
        if motifG:
            for dt, n in motif: pluck(bar + dt, n, motifG, -.25 + dt * .25, .26)
        for k in range(8):
            s = bar + k * .25
            if s >= t1: break
            if k * .25 in kickpat: kick(s, .4)
            if claps and k in (2, 6): clap(s)
            if hats: hat(s + (.125 if hats == 1 else 0), .022 if k % 2 else .03, .3)
            if hats == 2: hat(s + .125, .016, -.2)
            if glitch and k in (3, 7): tickp(s + .1875, .025, 6000, .4)
        if bassOn:
            r = rt(bar); pat = [(0, .22), (.75, .12), (1.0, .2), (1.5, .12), (1.75, .1)]
            for dt, dd in pat:
                if bar + dt < t1: bass(bar + dt, dd, r if dt != 1.75 else r[:-1] + str(int(r[-1]) + 1), .14, .3 if dt == 0 else 0)
        b += 2
if not os.path.exists(os.path.join(ROOT, 'build', 'music.wav')):
    section(0.0, 4.0, [0.0], False, 1, False, .075, .035)                 # hook: motif + tight hats
    for b in (1.0, 3.0): clap(b, .07)
    section(4.0, 8.0, [0.0, 1.0], True, 1, True, .05, .04, True)          # groove establishes
    section(8.0, 16.0, [0.0, .5, 1.0, 1.5], True, 2, True, .04, .045, True)  # fuller for the transformation
    section(16.0, 22.0, [0.0, .5, 1.0, 1.5], True, 1, True, .028, .04)    # space for narration
    section(22.0, 25.3, [0.0, .5, 1.0, 1.5], True, 2, True, .05, .05, True)  # lift for the range
    for s in np.arange(24.5, 25.3, .125): hat(s, .02, .1, op=(s % .5 == 0))
    riser(24.6, 25.3, .08)
    pad(25.3, 27.45, ['F2', 'C3', 'A3', 'E4'], .045, 700, att=.2, pump=False)  # reduce before "You create."
    for s in (25.3, 26.3): kick(s, .22)
    bass(25.3, 1.9, 'F1', .1)
    swell(28.3, C['hit'], .14)
    # payoff + resolve
    pad(C['hit'], 32.0, ['F2', 'C3', 'A3', 'E4', 'G4'], .07, 2600, att=.03, rel=.6, pump=False)
    bass(C['hit'], 1.2, 'F1', .2, .4)
    for i, (dt, n) in enumerate([(.5, 'C5'), (.75, 'D5'), (1.0, 'F5'), (1.5, 'D5'), (1.75, 'C5'), (2.0, 'A4'), (2.25, 'C5'), (2.75, 'F5')]):
        pluck(C['hit'] + dt + .25, n, .05, -.3 + i * .08, .35)
    for s in np.arange(C['hit'] + .5, 31.2, .5): hat(s, .015, .2)
    kick(C['hit'] + 1.0, .2); kick(C['hit'] + 2.0, .16)

# ------------------------------------------------------------ sound design (every sound has a visible source)
for k in range(0, 27, 2): tick(C['micro'] + k * .02, .035, -.4)                           # microtype typing
thump(C['catLand'], .3, 130, 60, .1); cloth(C['catLand'] - .2, .3, .06)                   # landing
mask(C['got'], .07, -.2); mask(C['got'] + .09, .05, -.1); mask(C['worth'], .06)            # mask reveals
tone(C['watching'], 1318.5, .05, .1, .08); whoosh(C['watching'] - .02, .3, .05, 1500, 7000, .4, -.1, .3)
tick(C['earFlick1'], .025, .3)
whoosh(C['hook1Out'] - .02, .3, .07, 900, 5000, 0, .3, .7)
mask(C['make'], .07, -.2); mask(C['make'] + .08, .05)
whoosh(C['looks'] + .1, .3, .06, 1200, 6000, -.3, .3, .4)                                  # marker swipe
thump(C['itHit'], .16, 150, 70, .08); tone(C['itHit'], 880, .04)                          # "it." lands
whoosh(C['hookOut'], .35, .08, 3000, 700, .2, -.3, .4); tone(C['hookOut'] + .2, 1567.98, .035)
cloth(C['S2'] - .1, .3, .07)                                                               # pose change
whoosh(C['card1'] - .05, .35, .14, 500, 3500, -.8, -.2, .6); thump(C['card1'] + .3, .1, 180, 90, .05)   # swing in
slide(C['card2'] - .06, .16, .22, 0); thump(C['card2'] + .2, .14, 140, 70, .06)                          # drops in
whoosh(C['card3'] - .1, .4, .12, 2500, 600, .4, .2, .7)                                                  # from depth
whoosh(C['cardsOut'], .5, .14, 300, 3000, .3, -.2, .6)                                     # card -> long-form
cloth(C['cardsOut'] + .15, .3, .05, -.6)
scrub(C['scrub'], C['select'] - .05, .06)
click(C['select'], .3, 2600, .2); tone(C['select'] + .02, 1760, .05, .2)
whoosh(C['lift'], .5, .1, 600, 2500, 0, -.3, .5)
cloth(C['tap'] - .12, .2, .05); click(C['tap'], .26, 3300, .3)                            # paw tap
for i in range(3): tick(C['pacing'] + i * .07, .06, -.2 + i * .2)                         # cut marks
riser(C['frame'], C['captions'] + .05, .06)
for i in range(5): tick(C['captions'] + .1 + i * .07, .05, .1)                            # caption ticks
whoosh(C['motion'], .22, .07, 2000, 9000, -.2, .3, .3); tone(C['visuals'], 1046.5, .05, .2)
pulse(C['sound'], .22); thump(C['sound'], .18, 110, 50, .14)                              # "...and sound."
chime(C['aveEdit'] + .02, [1046.5, 1318.5, 1568, 2093], .2, .035, .7)
whoosh(C['pullBack'], .5, .12, 3000, 500, .2, -.2, .3)
for i in range(5): tick(C['pullBack'] + .15 + abs(i - 2) * .08, .03, -.6 + i * .3)
tone(C['posted'], 1318.5, .07, 0); tone(C['posted'] + .05, 1975.5, .05, 0)                # posted ✓
riser(C['watched'] - .6, C['watched'], .07); mask(C['watched'], .08); whoosh(C['watched'] + .12, .35, .07, 1200, 6000, -.3, .3, .4)
whoosh(C['comedy'] - .14, .3, .26, 300, 5000, -.8, .8, .55); thump(C['kbPunch'], .2, 160, 60, .08)
whoosh(C['podcast'] - .14, .3, .24, 300, 5000, .8, -.8, .55)
whoosh(C['motionIn'] - .14, .3, .24, 300, 5000, -.8, .8, .55)
cloth(C['motionIn'] + .15, .3, .05, .5)
cloth(C['kfDrag'] - .1, .25, .05, .4); click(C['kfDrag'], .12, 2400, .4)                 # paw drags keyframe
click(C['motionPlay'], .18, 3000, -.2); tone(C['motionPlay'] + .03, 1567.98, .05, -.2)   # motion toggle
pulse(C['waveOn'], .13)
click(C['publish'], .28, 2800, .4); thump(C['publish'], .1, 200, 120, .04)              # publish tap
whoosh(C['motionOut'], .25, .14, 5000, 300, 0, 0, .3)                                    # collapse -> black
thump(C['youCreate'], .07, 70, 50, .3)
swell(C['hit'] - .45, C['hit'], .14)
hit(C['hit'], .36)
whoosh(C['S8'], .46, .1, 4000, 600, .4, -.3, .4)
chime(C['S8'] + .2, [1046.5, 1568], .12, .06, .9)                                         # branded end sound
chime(C['cta'], [1568, 2349.3], .14, .07, .5); click(C['cta'], .07, 2600)
cloth(C['wave1'], .5, .03)

# ------------------------------------------------------------ real clip audio bridges (low, under the voice)
def readwav(p, ch=1):
    w = wave.open(p); n = w.getnchannels(); x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    return x.reshape(-1, n)
def clipaudio(name, src_off, t0, d, g):
    x = readwav(os.path.join(CLIPA, name + '.wav')); i = int(src_off * SR); y = x[i:i + int(d * SR)].copy()
    f = int(.08 * SR); y[:f] *= np.linspace(0, 1, f)[:, None]; y[-f:] *= np.linspace(1, 0, f)[:, None]
    if y.shape[1] == 1: y = np.repeat(y, 2, 1)
    add(clipbus, t0, y, g)
clipaudio('kt', .4, C['comedy'], C['podcast'] - C['comedy'] + .08, .28)
clipaudio('sp', .1, C['podcast'], C['motionIn'] - C['podcast'] + .08, .22)

# ------------------------------------------------------------ voice (Jane Perry) — natural delivery, no time-stretch
def vofile(name):
    x = readwav(os.path.join(VO, name + '.wav'))[:, 0]; x = hp(x, 90, 2); return x + .22 * bp(x, 2500, 6500)
def place(name, seg, onset, target, g=1.0):
    x = vofile(name); i, j = int(seg[0] * SR), min(len(x), int(seg[1] * SR)); y = x[i:j].copy()
    f = int(.012 * SR); y[:f] *= np.linspace(0, 1, f); y[-f:] *= np.linspace(1, 0, f)
    add(vox, target - (onset - seg[0]), y, g)
place('jp1', (0, 1.45), .05, C['got'])
place('jp2', (0, 1.45), .04, C['make'])
place('jp3', (0, .78), .04, C['card1']); place('jp3', (.9, 1.95), .98, C['card2']); place('jp3', (2.0, 3.37), 2.10, C['card3'])
place('jp4', (0, 1.4), .05, C['footage']); place('jp4', (1.75, 3.92), 1.86, C['moments'])
place('jp5', (0, 3.4), .05, C['pacing'] - .67); place('jp5', (3.85, 4.86), 3.97, C['and'])
place('jp6', (0, 2.4), .05, 16.85); place('jp6', (2.6, 3.79), 2.72, C['watched'] - .33)
place('jp7', (0, .9), .05, 21.0); place('jp7', (.92, 1.93), 1.01, 21.95); place('jp7', (1.95, 2.87), 2.02, 22.95); place('jp7', (2.87, 4.02), 2.90, C['oneStudio'])
place('jp8', (0, 1.62), .07, C['youCreate']); place('jp8', (1.95, 3.6), 2.06, C['hit'] - .81)
place('jp9', (0, 2.25), .08, C['tagline'])

# ------------------------------------------------------------ mix
if os.path.exists(os.path.join(ROOT, 'build', 'music.wav')):
    m = readwav(os.path.join(ROOT, 'build', 'music.wav'))
    if m.shape[1] == 1: m = np.repeat(m, 2, 1)
    music[:min(N, len(m))] += m[:N] * .9
def env(x, win=.03):
    a = np.abs(x).max(1); k = int(win * SR); return np.sqrt(np.convolve(a ** 2, np.ones(k) / k, 'same'))
act = np.clip(env(vox) / .02, 0, 1); g = np.zeros_like(act); s = 0; ac, rc = np.exp(-1 / (.03 * SR)), np.exp(-1 / (.3 * SR))
for i in range(len(act)):
    v = act[i]; c = ac if v > s else rc; s = c * s + (1 - c) * v; g[i] = s
duck = 1 - .6 * g
# music arc: lower under narration, lift in gaps; dip before "You create.", drop before the hit
arc = np.ones(N, np.float32)
for t0, t1, v in [(25.3, C['drop'], .7), (C['drop'], C['hit'], .25), (29.3, 32.0, .85)]:
    arc[int(t0 * SR):int(t1 * SR)] = v
arc = np.convolve(arc, np.ones(3000) / 3000, 'same')
vn = .30 / (np.percentile(np.abs(vox[np.abs(vox).max(1) > 1e-3]).max(1), 99) + 1e-9)
mix = .45 * music * (duck * arc)[:, None] + sfx * (1 - .3 * g)[:, None] + clipbus * (1 - .55 * g)[:, None] + vox * vn
fo = int(.4 * SR); mix[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 1.5
mix = np.tanh(mix * 1.1) / 1.1
os.makedirs(os.path.join(ROOT, 'build'), exist_ok=True)
def wwav(p, x):
    y = np.clip(x, -1, 1); w = wave.open(p, 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((y * 32767).astype(np.int16).tobytes()); w.close()
wwav(os.path.join(ROOT, 'build', 'mix_raw.wav'), mix)
if '--report' in sys.argv:
    def db(x): return 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9)
    names = ['S1', 'S2', 'S3', 'S4', 'S5', 'S6', 'S7', 'S8']; bounds = [C[n] for n in names] + [DUR]
    for k, n in enumerate(names):
        i, j = int(bounds[k] * SR), int(bounds[k + 1] * SR)
        print(f"{n}: voice {db(vox[i:j]*vn):6.1f}  music {db(.45*(music*(duck*arc)[:,None])[i:j]):6.1f}  sfx {db(sfx[i:j]):6.1f}  clips {db(clipbus[i:j]):6.1f}")
    # check voice lines never overlap
    on = np.abs(vox).max(1) > 1e-4
print('ok')
