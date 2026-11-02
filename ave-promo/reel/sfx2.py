# Reel sound design v2 — modelled on the reference: warm, low-weighted transitions (sub boom + soft
# low-passed swoosh + reverse swell), gentle UI pops; almost no top-end hiss. Writes into the `sfx` bus.
# Every effect is tied to a visible event on screen (cues.js).
from scipy.signal import fftconvolve
R2 = np.random.default_rng(29)
def nz(d): return R2.standard_normal(int(d * SR))
def env_ad(n, a, d):
    t = np.arange(n) / SR; return np.minimum(1, t / max(a, 1e-4)) * np.exp(-np.maximum(0, t - a) / d)
def put(t0, x, g=1., pan=0.):
    add(sfx, t0, x, g, pan)
def sweep_bp(x, f0, f1, q=1.6, seg=384):
    y = np.zeros_like(x); n = len(x)
    for i in range(0, n, seg):
        fc = f0 * (f1 / f0) ** (i / max(1, n)); lo, hi = fc / q, min(fc * q, SR / 2 - 200)
        y[i:i + seg] = bp(x[max(0, i - 1024):i + seg], lo, hi)[-len(x[i:i + seg]):]
    return y
# --- building blocks
def boom(t0, g=.5, f0=60, f1=38, dec=.22):               # deep sub drop, the reference's main cut sound
    t = tv(dec * 4); f = f1 + (f0 - f1) * np.exp(-t / .07)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR); x = np.tanh(1.6 * x) * np.exp(-t / dec)
    x += .35 * lp(nz(dec * 4), 180) * np.exp(-t / .05)        # body
    x *= np.minimum(1, t / .002); put(t0, x, g)
def swoosh(t0, d=.32, g=.25, f0=250, f1=2200, pan0=-.6, pan1=.6, peak=.7):   # soft air move, low-passed
    t = tv(d); x = sweep_bp(nz(d), f0, f1, 1.8); x = lp(x, 3200)
    e = np.where(t / d < peak, (t / d / peak) ** 2.2, ((1 - t / d) / (1 - peak)) ** 1.4)
    pn = np.linspace(pan0, pan1, len(t)); y = x * e * 1.6
    put(t0, np.stack([y * np.cos((pn + 1) * np.pi / 4), y * np.sin((pn + 1) * np.pi / 4)], 1) * 1.414, g)
def swell(t0, t1, g=.18):                                  # reverse-cymbal style suck into a hit
    d = t1 - t0; t = tv(d); x = lp(hp(nz(d), 900), 6000) * (t / d) ** 3.2
    x += .5 * np.sin(2 * np.pi * np.cumsum(90 * 3 ** (t / d)) / SR) * (t / d) ** 2.5
    x[-int(.025 * SR):] *= np.linspace(1, 0, int(.025 * SR)); put(t0, x, g)
def thock(t0, g=.2, f=170):                                # soft wooden UI knock
    t = tv(.18); x = np.sin(2 * np.pi * f * t * (1 + .6 * np.exp(-t / .01))) * np.exp(-t / .045) + .3 * lp(nz(.18), 1500) * np.exp(-t / .01)
    put(t0, x, g)
def pop(t0, g=.12, f=900, pan=0.):                         # bubbly pop (stars, chips)
    t = tv(.12); x = np.sin(2 * np.pi * np.cumsum(f * (1 + 1.2 * np.exp(-t / .012))) / SR) * np.exp(-t / .03)
    put(t0, x * np.minimum(1, t / .001), g, pan)
def tick2(t0, g=.06, pan=0.):                              # soft tick (number roll)
    t = tv(.05); x = bp(nz(.05), 1500, 4000) * np.exp(-t / .006) + .4 * np.sin(2 * np.pi * 900 * t) * np.exp(-t / .01)
    put(t0, x, g, pan)
def key(t0, g=.1, pan=0.):                                 # keyboard key: click + thock
    tick2(t0, g * .8, pan); thock(t0 + .012, g * .6, 220)
def glitch2(t0, n=10, g=.06):                              # digital data bursts (pixel opening)
    for k in range(n):
        d = .012 + .01 * R2.random(); t = tv(d); f = 300 + 1700 * R2.random()
        x = np.sign(np.sin(2 * np.pi * f * t)) * .5 + .5 * lp(nz(d), 3000)
        x = np.round(x * 6) / 6 * np.exp(-t / (d * .6)); put(t0 + k * .03 + .008 * R2.random(), lp(x, 5000), g * (1 - .5 * k / n), (-1) ** k * .5)
def marker(t0, d=.3, g=.12):                               # felt marker swipe
    t = tv(d); x = bp(nz(d), 1800, 5500) * np.sin(np.pi * t / d) ** 1.5 * (1 + .3 * np.sin(2 * np.pi * 38 * t)); put(t0, x, g, .2)
def shutter(t0, g=.18):                                    # playhead lands
    thock(t0, g, 260); tick2(t0 + .035, g * .5)
def bloom(t0, g=.1, f=520):                                # soft tonal bloom for reveals (no music, so this is the "sting")
    t = tv(1.4); x = sum(np.sin(2 * np.pi * f * m * t) * w for m, w in [(1, 1), (1.5, .5), (2, .35), (3, .15)]) * np.exp(-t / .3) * np.minimum(1, t / .01)
    put(t0, lp(x, 4000), g)
def transition(c, g=1.):                                   # the reference's cut: swell → swoosh → boom
    swell(c - .38, c - .01, .14 * g); swoosh(c - .2, .34, .32 * g, 180, 1800); boom(c, .5 * g)
# --- placement on the picture cues
glitch2(.04, 12, .07)                                       # pixel blocks flicker on
swoosh(C['icon'] - .05, .45, .22, 150, 1200, 0, 0, .55); boom(C['icon'] + .2, .2, 70, 48, .18)   # icon resolves
for k in range(16): tick2(C['roll'] + k * .05, .04 + .002 * k, .15)   # number rolls up
t_ = tv(C['hot'] - C['roll']); put(C['roll'], lp(np.sin(2 * np.pi * np.cumsum(120 * 3 ** (t_ / t_[-1])) / SR), 900) * (t_ / t_[-1]) ** 2 * .6, .05)   # heat rising (low hum, not a whine)
for i in range(5): pop(C['cap'] + i * .12, .05, 600 + 40 * i, -.2 + .1 * i)
for c in CUTS[:4]: transition(c)
transition(C['white'], .9); bloom(C['white'] + .02, .08, 440)
for st, *_ in C['SHOTS']:                                   # clip changes inside the card: small whoosh + knock
    if all(abs(st - c) > .02 for c in CUTS): swoosh(st - .1, .18, .15, 300, 1500, .4, -.4, .6); thock(st, .12, 190)
thock(C['title1'], .22, 150); pop(C['title1'] + .03, .08, 700)
for c in CUTS[:4]:
    for i in range(5): pop(c + .12 + i * .045, .045, 900 + 60 * i, -.4 + .2 * i)   # stars
for k in range(7): tick2(C['white'] + .05 + k * .1, .05, -.4 + .12 * k)           # filmstrip scrub
shutter(C['stop'], .2)
boom(C['slam'], .32, 64, 40, .2); thock(C['slam'], .25, 140); thock(C['slam'] + .07, .2, 140)   # EVERY FRAME, slams
marker(C['purpose'] + .1, .32, .14)                        # lime marker swipe
swoosh(C['lock'] - .25, .4, .26, 200, 1600, .5, -.5, .6); boom(C['logo'] + .05, .3, 56, 38, .25)   # logo lockup
for i in range(6): tick2(C['studio'] + i * .045, .035, -.3 + .12 * i)
swoosh(C['rule'], .3, .1, 400, 2000, -.6, .6, .5)
swoosh(C['dm'] - .05, .35, .16, 200, 1200, 0, 0, .6); thock(C['dm'] + .2, .12, 200)
for k in range(6): key(C['type'] + k * .075, .12, .1)       # S-A-M-P-L-E
thock(C['send'] - .02, .2, 230); swoosh(C['send'], .3, .2, 400, 2600, -.2, .7, .4); pop(C['send'] + .05, .1, 1100)
bloom(C['send'] + .12, .07, 660)
# short room so the effects sit in a space instead of feeling dry
ir_t = tv(.45); ir = R2.standard_normal(len(ir_t)) * np.exp(-ir_t / .11); ir /= np.sqrt((ir ** 2).sum())
for ch in (0, 1): sfx[:, ch] += .18 * fftconvolve(lp(sfx[:, ch], 5000), ir, 'full')[:N].astype(np.float32)
