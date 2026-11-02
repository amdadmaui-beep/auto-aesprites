# Reel sound design v3 — built from the supplied "Free UI SaaS SFX" pack (sfx/ui_saas_demo.wav, sliced below),
# with a few code-made layers (sub weight, marker swipe) where the pack has no matching sound.
_s = open(os.path.join(HERE, 'sfx2.py')).read(); exec(_s[:_s.index('# --- placement')])
def _rd(p):
    w = wave.open(p); return np.frombuffer(w.readframes(w.getnframes()), np.int16).reshape(-1, w.getnchannels()).astype(np.float32) / 32768
PACK = _rd(os.path.join(HERE, 'sfx', 'ui_saas_demo.wav'))
def cut(a, b, fi=.002, fo=.03):
    y = PACK[int(a * SR):int(b * SR)].copy(); n1, n2 = int(fi * SR), int(fo * SR)
    y[:n1] *= np.linspace(0, 1, n1)[:, None]; y[-n2:] *= np.linspace(1, 0, n2)[:, None]; return y
# the pack's sounds
LOWHITS = [0.128, 0.172, 0.272, 0.332, 0.400, 0.460, 0.572, 0.670, 0.886, 0.974, 1.024, 1.084, 1.242, 1.466, 1.774]
TICKS = [5.772, 5.838, 5.914, 5.958, 6.006, 6.060, 6.122, 6.192, 6.276, 6.382, 6.502, 6.636]
def lowhit(k, dur=.2): a = LOWHITS[k % len(LOWHITS)]; return cut(a - .004, a + dur)
def tickk(k): a = TICKS[k % len(TICKS)]; return cut(a - .003, a + .06, .001, .02)
CHIME = cut(2.70, 4.10, .002, .25)                 # bright hit + ring       (peak at 0.01)
GLITCH = cut(4.16, 4.55, .002, .04)                # digital glitch         (peak at ~0.01)
RISE = cut(7.30, 8.30, .01, .45)                    # riser into a whoosh    (peak at 0.37)
RISE_PEAK = .37
def P_(t0, y, g=1., pan=0.):
    if pan: y = y * np.array([np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)]) * 1.414
    add(sfx, t0, y, g)
# ASMR layers: close, dry, tactile detail on top of the pack sounds
def asmr_tap(t0, g=.18, pan=0., bright=1.):
    t = tv(.08); x = bp(nz(.08), 2200, 9500) * np.exp(-t / (.003 + .002 * (1 - bright))) * 1.4
    x += .5 * np.sin(2 * np.pi * 150 * t) * np.exp(-t / .012); x += .25 * bp(nz(.08), 600, 1800) * np.exp(-t / .006)
    P_(t0, np.stack([x, x], 1), g, pan)
def asmr_brush(t0, d=.22, g=.14, pan0=-.3, pan1=.3):          # soft card/paper slide: grainy, airy, close
    n = int(d * SR); t = np.arange(n) / SR; z = nz(d)
    grains = np.zeros(n)
    for k in range(int(d * 260)):                               # tiny friction grains
        i = int(R2.random() * (n - 200)); L_ = 40 + int(R2.random() * 120); grains[i:i + L_] += R2.standard_normal(L_) * np.hanning(L_) * (.4 + R2.random())
    x = bp(z, 2500, 11000) * .35 + bp(grains, 1800, 10000)
    x *= np.sin(np.pi * t / d) ** 1.6; pn = np.linspace(pan0, pan1, n)
    P_(t0, np.stack([x * np.cos((pn + 1) * np.pi / 4), x * np.sin((pn + 1) * np.pi / 4)], 1) * 1.414, g)
# --- placement on the picture cues
P_(0.0, cut(0.10, 0.75, .002, .12), .55)                                  # pixel blocks: the pack's low hit run
P_(C['icon'] + .02, GLITCH, .35)
for k in range(16): P_(C['roll'] + k * .05, tickk(k), .4 + .02 * k); asmr_tap(C['roll'] + k * .05, .06 + .004 * k, (-1) ** k * .3)       # number rolls (pack ticks)
for i in range(5): P_(C['cap'] + i * .12, tickk(i + 3), .25, -.2 + .1 * i); asmr_tap(C['cap'] + i * .12, .1, -.3 + .15 * i)
for c in CUTS:                                                            # colour cuts: pack riser lands on the cut, + sub weight
    P_(c - RISE_PEAK, RISE, .7); P_(c, lowhit(0, .35), .7); boom(c, .28, 58, 38, .2)
for st, *_ in C['SHOTS']:                                                 # clip changes inside the card: pack glitch
    if all(abs(st - c) > .02 for c in CUTS): asmr_brush(st - .14, .2, .16, .4, -.3); asmr_tap(st, .2, .1)
P_(C['title1'], CHIME, .4)                                                # "Impact" lands
for c in CUTS[:4]:
    for i in range(5): P_(c + .12 + i * .05, tickk(i), .25, -.4 + .2 * i); asmr_tap(c + .12 + i * .05, .09, -.5 + .25 * i)   # stars
for k in range(7): P_(C['white'] + .05 + k * .1, tickk(k + 4), .3, -.4 + .12 * k); asmr_tap(C['white'] + .05 + k * .1, .07, -.4 + .12 * k)   # filmstrip scrub
P_(C['stop'], lowhit(4), .5)
P_(C['slam'], lowhit(2, .3), .8); P_(C['slam'] + .07, lowhit(5, .3), .7); boom(C['slam'], .2, 64, 40, .18)
asmr_brush(C['purpose'] + .1, .34, .3, -.5, .5)                          # marker swipe, close and grainy
P_(C['logo'] - RISE_PEAK + .05, RISE, .6); P_(C['logo'] + .05, CHIME, .45)
for i in range(6): P_(C['studio'] + i * .045, tickk(i + 2), .18, -.3 + .12 * i)
asmr_brush(C['dm'] + .02, .25, .18, 0, 0); asmr_tap(C['dm'] + .25, .18)
for k in range(6): P_(C['type'] + k * .075, tickk(k), .45, .1); asmr_tap(C['type'] + k * .075, .2, -.2 + .08 * k)   # S-A-M-P-L-E
P_(C['send'], CHIME, .5); P_(C['send'], lowhit(1), .4); asmr_tap(C['send'] - .02, .25)
ir_t = tv(.4); ir = R2.standard_normal(len(ir_t)) * np.exp(-ir_t / .1); ir /= np.sqrt((ir ** 2).sum())
for ch in (0, 1): sfx[:, ch] += .05 * fftconvolve(lp(sfx[:, ch], 6000), ir, 'full')[:N].astype(np.float32)
