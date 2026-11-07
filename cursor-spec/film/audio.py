# Cursor spec commercial — original score + sound design, placed from cues.js. Writes stems:
#   build/music.wav, build/sfx.wav, build/mix_raw.wav (music + sfx), build/nomusic_raw.wav (sfx only)
# SFX: designed in code, plus slices of the supplied UI SaaS SFX pack (sfx/ui_saas_demo.wav).
import json, re, os, wave, sys
import numpy as np
from scipy import signal
from scipy.signal import fftconvolve
HERE = os.path.dirname(os.path.abspath(__file__)); SR = 48000
src = open(os.path.join(HERE, 'cues.js')).read(); body = re.sub(r'//[^\n]*', '', src[src.index('{'):src.rindex('}') + 1])
C = json.loads(re.sub(r'([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:', r'\1"\2":', body))
N = int(C['dur'] * SR); rng = np.random.default_rng(17)
music = np.zeros((N, 2), np.float32); sfx = np.zeros((N, 2), np.float32); verb = np.zeros((N, 2), np.float32)
def tv(d): return np.arange(int(d * SR)) / SR
def nz(d): return rng.standard_normal(int(d * SR))
def lp(x, f, o=2): b, a = signal.butter(o, min(f, SR / 2 - 100) / (SR / 2), 'low'); return signal.lfilter(b, a, x)
def hp(x, f, o=2): b, a = signal.butter(o, f / (SR / 2), 'high'); return signal.lfilter(b, a, x)
def bp(x, f1, f2, o=2): b, a = signal.butter(o, [f1 / (SR / 2), min(f2, SR / 2 - 100) / (SR / 2)], 'band'); return signal.lfilter(b, a, x)
def add(bus, t0, x, g=1., pan=0., rv=0.):
    if x.ndim == 1: x = np.stack([x * np.cos((pan + 1) * np.pi / 4), x * np.sin((pan + 1) * np.pi / 4)], 1) * 1.414
    i = int(round(t0 * SR));
    if i < 0: x = x[-i:]; i = 0
    j = min(N, i + len(x))
    if j > i: bus[i:j] += (x[:j - i] * g).astype(np.float32);
    if rv and j > i: verb[i:j] += (x[:j - i] * g * rv).astype(np.float32)
def nf(n):
    m = {'C':0,'C#':1,'Db':1,'D':2,'Eb':3,'E':4,'F':5,'F#':6,'Gb':6,'G':7,'Ab':8,'A':9,'Bb':10,'B':11}
    return 440 * 2 ** ((12 * (int(n[-1]) + 1) + m[n[:-1]] - 69) / 12)
# ------------------------------------------------ the supplied pack (sliced)
w = wave.open(os.path.join(HERE, 'sfx', 'ui_saas_demo.wav')); PACK = np.frombuffer(w.readframes(w.getnframes()), np.int16).reshape(-1, 2).astype(np.float32) / 32768
def cut(a, b, fi=.002, fo=.03):
    y = PACK[int(a * SR):int(b * SR)].copy(); n1, n2 = int(fi * SR), int(fo * SR); y[:n1] *= np.linspace(0, 1, n1)[:, None]; y[-n2:] *= np.linspace(1, 0, n2)[:, None]; return y
TICKS = [5.772, 5.838, 5.914, 5.958, 6.006, 6.060, 6.122, 6.192, 6.276, 6.382, 6.502, 6.636]
def pack_tick(k): a = TICKS[k % len(TICKS)]; return cut(a - .003, a + .06, .001, .02)
PACK_CHIME = cut(2.70, 4.10, .002, .25); PACK_RISE = cut(7.30, 8.30, .01, .45)
# ------------------------------------------------ designed SFX (layer A micro, B motion, C cinematic)
def key(t0, g=.5, pan=0., k=0):                     # mechanical key: bright click + plastic body + soft bottom-out
    r = np.random.default_rng(int(t0 * 1000)); t = tv(.09); f = 3200 + 900 * r.random()
    x = bp(r.standard_normal(len(t)), f * .6, f * 1.8) * np.exp(-t / .0035) * .55
    x += .55 * np.sin(2 * np.pi * (230 + 40 * r.random()) * t) * np.exp(-t / .016)
    x += .25 * lp(r.standard_normal(len(t)), 1400) * np.exp(-t / .01)
    add(sfx, t0, x, g * (.8 + .4 * r.random()), pan + (r.random() - .5) * .2)
def tabkey(t0, g=.9):                               # the Tab press: deeper, longer travel, crisp top
    t = tv(.22); x = np.sin(2 * np.pi * 150 * t * (1 + .4 * np.exp(-t / .01))) * np.exp(-t / .045)
    x += .9 * bp(nz(.22), 2000, 7000) * np.exp(-t / .004) + .4 * lp(nz(.22), 900) * np.exp(-t / .02)
    add(sfx, t0, x, g); add(sfx, t0 + .055, .5 * np.sin(2 * np.pi * 170 * tv(.08)) * np.exp(-tv(.08) / .02), g * .5)   # release
def pop(t0, g=.3, f0=900, f1=520, pan=0.):          # creamy UI pop
    t = tv(.25); f = f1 + (f0 - f1) * np.exp(-t / .02); x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / .05) * np.minimum(1, t / .002)
    x += .35 * np.sin(2 * np.pi * np.cumsum(f * .5) / SR) * np.exp(-t / .07); add(sfx, t0, x, g, pan)
def snap(t0, g=.4, pan=0., f=210):                  # magnetic panel snap: soft thock + tiny metallic tick
    t = tv(.16); x = np.sin(2 * np.pi * f * t * (1 + .5 * np.exp(-t / .008))) * np.exp(-t / .03) + .5 * bp(nz(.16), 4000, 11000) * np.exp(-t / .002)
    add(sfx, t0, x, g, pan, .15)
def glass(t0, g=.25, f=2400, pan=0.):               # glass-like interface click
    t = tv(.5); x = (np.sin(2 * np.pi * f * t) + .5 * np.sin(2 * np.pi * f * 2.76 * t) + .3 * np.sin(2 * np.pi * f * 5.4 * t)) * np.exp(-t / .07)
    x += .4 * bp(nz(.5), 5000, 12000) * np.exp(-t / .003); add(sfx, t0, x * np.minimum(1, t / .0008), g, pan, .3)
def whoosh(t0, d=.4, g=.25, f0=300, f1=2400, p0=-.6, p1=.6, peak=.6):
    t = tv(d); x = nz(d); y = np.zeros_like(x); seg = 384
    for i in range(0, len(x), seg):
        fc = f0 * (f1 / f0) ** (i / len(x)); y[i:i + seg] = bp(x[max(0, i - 1024):i + seg], fc / 1.7, min(fc * 1.7, 18000))[-len(x[i:i + seg]):]
    y = lp(y, 4500); e = np.where(t / d < peak, (t / d / peak) ** 2.2, ((1 - t / d) / (1 - peak)) ** 1.4); pn = np.linspace(p0, p1, len(t))
    add(sfx, t0, np.stack([y * e * np.cos((pn + 1) * np.pi / 4), y * e * np.sin((pn + 1) * np.pi / 4)], 1) * 2.0, g, 0, .2)
def suck(t0, t1, g=.35):                            # tight reverse suction into a hit
    d = t1 - t0; t = tv(d); x = lp(hp(nz(d), 700), 7000) * (t / d) ** 4 + .4 * np.sin(2 * np.pi * np.cumsum(120 * 4 ** (t / d)) / SR) * (t / d) ** 3
    x[-int(.012 * SR):] *= np.linspace(1, 0, int(.012 * SR)); add(sfx, t0, x, g)
def boom(t0, g=.6, f0=62, f1=38, dec=.35):          # deep, clean sub impact (no distortion)
    t = tv(dec * 4); f = f1 + (f0 - f1) * np.exp(-t / .06); x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / dec)
    x += .3 * lp(nz(dec * 4), 200) * np.exp(-t / .03); x *= np.minimum(1, t / .002); add(sfx, t0, x, g, 0, .1)
def shimmer(t0, g=.12, f=1760, d=.9, pan=0.):       # short digital shimmer
    t = tv(d); x = sum(np.sin(2 * np.pi * f * m * t + 3 * m) * w_ for m, w_ in [(1, 1), (1.5, .55), (2.01, .35), (3, .18)]) * np.exp(-t / (d / 3))
    x *= (1 + .3 * np.sin(2 * np.pi * 9 * t)) * np.minimum(1, t / .01); add(sfx, t0, x, g, pan, .5)
def riser(t0, t1, g=.12):
    d = t1 - t0; t = tv(d); x = lp(np.sin(2 * np.pi * np.cumsum(55 * 2 ** (1.5 * t / d)) / SR), 600) * (t / d) ** 2 + .3 * lp(hp(nz(d), 400), 3000) * (t / d) ** 3
    add(sfx, t0, x, g, 0, .2)
def tick(t0, g=.12, pan=0.): add(sfx, t0, pack_tick(int(t0 * 97)), g * 2.2, pan)
def sonic_logo(t0):                                 # one deep, exceptionally clean hit + a quiet resolving chord
    boom(t0, .85, 70, 36, .55)
    t = tv(3.5)
    for i, n in enumerate(['D3', 'A3', 'E4', 'F#4', 'A4']):
        f = nf(n); x = (np.sin(2 * np.pi * f * t) + .25 * np.sin(2 * np.pi * 2 * f * t)) * np.exp(-t / 1.4) * np.minimum(1, t / (.01 + .02 * i))
        add(sfx, t0 + .02 * i, x, .05, -.4 + .2 * i, .6)
    shimmer(t0 + .05, .07, 2349, 2.0)
# ------------------------------------------------ score: minimal, warm electronic (D major / B minor colour), 100 BPM
BEAT = .6; GRID0 = C['faster'] - 41 * BEAT          # the grid lands a downbeat exactly on "FASTER."
def grid(a, b, step=1.0):
    k0 = int(np.ceil((a - GRID0) / (BEAT * step))); out = []
    while GRID0 + k0 * BEAT * step < b: out.append(GRID0 + k0 * BEAT * step); k0 += 1
    return out
def kick(t0, g=.5):
    t = tv(.45); f = 44 + 100 * np.exp(-t / .03); x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / .2) + .25 * bp(nz(.45), 2000, 8000) * np.exp(-t / .002)
    add(music, t0, x, g)
def hat(t0, g=.03, pan=.3, dec=.025): add(music, t0, hp(nz(.3), 8000) * np.exp(-tv(.3) / dec), g, pan)
def clap(t0, g=.12):
    t = tv(.4); x = np.zeros_like(t)
    for d in (0, .009, .018): x += np.roll(bp(nz(.4), 1000, 5000) * np.exp(-t / .01), int(d * SR))
    add(music, t0, x + .5 * bp(nz(.4), 1200, 6000) * np.exp(-t / .1), g, -.05, .35)
def bass(t0, d, n, g=.22):
    f = nf(n); t = tv(d + .05); x = np.sin(2 * np.pi * f * t) + .3 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t / .1)
    x *= np.minimum(1, t / .006) * np.clip((d + .04 - t) / .04, 0, 1); add(music, t0, lp(x, 500), g)
def pluck(t0, n, g=.06, pan=0., dec=.35):
    f = nf(n); t = tv(1.4); x = np.sin(2 * np.pi * f * t + 1.4 * np.exp(-t / .04) * np.sin(2 * np.pi * 2 * f * t)) * np.exp(-t / dec)
    add(music, t0, x * np.minimum(1, t / .002), g, pan, .45)
def pad(t0, t1, notes, g=.05, cut=1200, att=.8, rel=1.2):
    d = t1 - t0 + rel; t = tv(d); L = np.zeros_like(t); R = np.zeros_like(t)
    for n in notes:
        f = nf(n); L += signal.sawtooth(2 * np.pi * f * .997 * t + rng.random() * 6); R += signal.sawtooth(2 * np.pi * f * 1.003 * t + rng.random() * 6)
    e = np.minimum(1, t / att) * np.where(t > t1 - t0, np.exp(-(t - (t1 - t0)) / (rel / 3)), 1)
    add(music, t0, np.stack([lp(L, cut), lp(R, cut)], 1) * e[:, None] / len(notes), g, 0, .3)
CH = [(['D3', 'F#3', 'A3', 'E4'], 'D2'), (['B2', 'D3', 'F#3', 'A3'], 'B1'), (['G2', 'B2', 'D3', 'F#3'], 'G1'), (['A2', 'C#3', 'E3', 'B3'], 'A1')]
def chord_at(t): return CH[int(np.floor((t - GRID0) / (4 * BEAT))) % 4]
ARP = ['A4', 'D5', 'E5', 'F#5', 'A5', 'F#5', 'E5', 'D5']
# 3.55 → 5.75: the world opens — a low pad swell
pad(C['open'], C['win'] + .3, ['D2', 'A2', 'D3', 'E3'], .06, 700, 1.4)
# 5.75 → 9.9: a pulse starts (soft kick on 1 and 3, sub, sparse plucks)
for b0 in grid(C['win'], C['s2out']):
    k = int(round((b0 - GRID0) / BEAT)); notes, root = chord_at(b0)
    if k % 2 == 0: kick(b0, .32)
    if k % 4 == 0: bass(b0, BEAT * 1.8, root, .18); pad(b0, b0 + 4 * BEAT - .05, notes, .035, 1000, .3, .5)
    hat(b0 + BEAT / 2, .012)
    if k % 2 == 1: pluck(b0, ARP[k % 8], .04, -.3 + .1 * (k % 6))
# 9.9 → 16.75: breathe for Tab — pad + gentle arpeggio, no drums
for b0 in grid(C['cam3'], C['s3out']):
    k = int(round((b0 - GRID0) / BEAT)); notes, root = chord_at(b0)
    if k % 4 == 0: pad(b0, b0 + 4 * BEAT - .05, notes, .04, 900, .4, .6); bass(b0, BEAT * 3.5, root, .1)
    pluck(b0 + BEAT / 2, ARP[(k * 3) % 8], .028, .3)
# 16.9 → 24.6: momentum — kick, 16th hats, syncopated bass, ticking
for b0 in grid(C['cam4'], C['push']):
    k = int(round((b0 - GRID0) / BEAT)); notes, root = chord_at(b0)
    kick(b0, .4 if k % 2 == 0 else .3)
    if k % 2 == 1: clap(b0, .08)
    for s in range(4): hat(b0 + s * BEAT / 4, .02 if s % 2 else .012, .3)
    bass(b0, BEAT * .45, root, .2); bass(b0 + BEAT * .75, BEAT * .22, root, .14)
    if k % 4 == 0: pad(b0, b0 + 4 * BEAT - .05, notes, .03, 1400, .2, .4)
riser(C['ready'], C['push'] + .05, .1)
# 24.75 → 32.7: the strongest section — full drums, stabs, arpeggio up an octave
for b0 in grid(C['full'], C['s5out']):
    k = int(round((b0 - GRID0) / BEAT)); notes, root = chord_at(b0)
    kick(b0, .5)
    if k % 2 == 1: clap(b0, .14)
    for s in range(4): hat(b0 + s * BEAT / 4, .026 if s % 2 else .016, .3)
    bass(b0, BEAT * .45, root, .26); bass(b0 + BEAT * .5, BEAT * .3, root[:-1] + str(int(root[-1]) + 1), .16)
    if k % 4 == 0: pad(b0, b0 + 4 * BEAT - .05, notes, .045, 2200, .1, .4)
    pluck(b0 + BEAT / 2, ARP[k % 8][:-1] + str(int(ARP[k % 8][-1]) + 1), .03, -.3 + .15 * (k % 5))
pad(C['s5out'], C['silence'] - .2, ['D3', 'A3', 'E4'], .04, 800, .1, .4)
# silence 34.35 → 34.9, then the sonic logo carries the end (no music under the brand hold)
# ------------------------------------------------ sound design placement
for k, t0 in enumerate(C['H1'] + C['H2']): key(t0, .55)
tick(C['caretOn'], .05)
suck(C['H2'][-1] + .02, C['dive'], .4); boom(C['dive'], .6); shimmer(C['dive'] + .02, .1, 1760)
whoosh(C['open'] - .05, .5, .22, 200, 1800, -.8, .8, .4)
riser(C['cube'], C['cube'] + 1.0, .1); glass(C['cube'] + .9, .2, 2100); shimmer(C['sweep'] + .1, .07, 2637, 1.2, .3)
whoosh(C['cubeOut'], .5, .14, 1800, 300, .2, .6, .5)
for i, p in enumerate(['p1', 'p2', 'p3', 'p4']): snap(C[p] + .32, .35, [-.6, 0, .6, 0][i], 190 + 25 * i); glass(C[p] + .34, .06, 2800 + 200 * i, [-.6, 0, .6, 0][i])
pop(C['meet'], .12, 700, 420); tick(C['speed'], .05)
whoosh(C['cam3'] - .1, .55, .14, 900, 250, .4, -.2, .4)
for t0 in C['T1']: key(t0, .4, .1)
shimmer(C['ghost1'], .045, 2093, .7, .2); pop(C['tabIn1'], .1, 650, 400, .3)
tabkey(C['tab1'], .45); pop(C['tab1'] + .03, .16, 1100, 700); shimmer(C['tab1'] + .06, .08, 2637, .9)
for t0 in C['T2']: key(t0, .38, .1)
shimmer(C['ghost2'], .04, 2349, .6, .2); pop(C['tabIn2'], .09, 650, 400, .3)
tabkey(C['tab2'], .42); pop(C['tab2'] + .03, .15, 1200, 760); shimmer(C['tab2'] + .06, .07, 2794, .8)
whoosh(C['cam4'] - .1, .5, .13, 300, 1500, -.4, .6, .5)
for i, t0 in enumerate(C['TP']):
    if i % 2 == 0: key(t0, .26, .4)
snap(C['send'], .4, .4, 240); pop(C['send'] + .02, .14, 950, 600, .4); whoosh(C['send'] + .05, .35, .08, 400, 1600, .5, .2, .5)
for st in ['st1', 'st2', 'st3', 'st3b', 'st4']: tick(C[st], .07, .4); snap(C[st] + .02, .18, -.1, 260)
for st in ['st2', 'st3', 'st3b', 'st4']: whoosh(C[st] - .06, .16, .06, 1200, 3000, .2, -.4, .5)
for st in ['st1', 'st2', 'st3', 'st3b', 'st4']: glass(C[st] + .45, .05, 3136, .4)       # step completes
key(C['term'] + .05, .3); key(C['term'] + .12, .3); snap(C['term'], .2, -.2, 180)
for i in range(4): tick(C['term'] + .35 + i * .12, .05, -.2)
pop(C['ready'], .14, 880, 560, -.2); glass(C['done'], .08, 2637, .4)
whoosh(C['preview'], .45, .12, 800, 2000, .7, -.2, .5); boom(C['preview'] + .3, .3, 55, 40, .25)
whoosh(C['push'] - .05, .65, .2, 160, 900, -.3, .3, .55); boom(C['full'], .45, 58, 38, .3)
for i in range(4): snap(C['cards'] + i * .09 + .1, .22, -.6 + .4 * i, 230 + 15 * i)
riser(C['line'], C['line'] + 1.3, .05)
for i in range(5): pop(C['bars'] + i * .08 + .12, .1, 760 + 60 * i, 480, -.5 + .25 * i)
pop(C['hover'] + .05, .12, 1000, 700, .2)
boom(C['faster'], .65, 64, 38, .32); glass(C['faster'] + .01, .06, 2349)
whoosh(C['fold'], .7, .18, 2000, 300, .5, -.3, .5)
for i in range(3): snap(C['fold'] + .25 + i * .14, .25, [-.4, .4, 0][i], 200 + 30 * i)
glass(C['cubeMorph'], .14, 1975)
sonic_logo(C['lockup'])
tick(C['future'], .04); tick(C['url'], .03)
# ------------------------------------------------ mix + stems
ir_t = tv(1.4); ir = rng.standard_normal(len(ir_t)) * np.exp(-ir_t / .32); ir /= np.sqrt((ir ** 2).sum())
wet = np.stack([fftconvolve(verb[:, c], ir * (1 if c else .97), 'full')[:N] for c in (0, 1)], 1).astype(np.float32) * .3
# reverb returns: split by source (music verb lives in music bus, sfx verb in sfx bus) — approximate by ratio
def rms(x): return float(np.sqrt(np.mean(x ** 2)) + 1e-9)
music_out = music * .55; sfx_out = sfx * 1.0 + wet
# no music under the silence beat and the brand hold
g = np.ones(N, np.float32); a, b = int(C['silence'] * SR), int(C['lockup'] * SR); f = int(.08 * SR)
g[a:] = 0; g[a - f:a] = np.linspace(1, 0, f); music_out *= g[:, None]
def lim(x): return np.tanh(x * 1.05) / 1.05
def ww(name, x):
    y = np.clip(x, -1, 1); w = wave.open(os.path.join(HERE, 'build', name), 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((y * 32767).astype(np.int16).tobytes()); w.close()
os.makedirs(os.path.join(HERE, 'build'), exist_ok=True)
fo = int(.3 * SR)
for x in (music_out, sfx_out): x[-fo:] *= np.linspace(1, 0, fo)[:, None]
# clean headroom: one gain for the whole mix (no saturation), stems share it so they sum back exactly
pk = float(np.abs(music_out + sfx_out).max()); hg = .89 / pk if pk > .89 else 1.0
music_out *= hg; sfx_out *= hg
pki = int(np.argmax(np.abs(music_out + sfx_out).max(1))); print('peak at', round(pki / SR, 2), 's, headroom gain', round(hg, 3))
ww('music.wav', music_out); ww('sfx.wav', sfx_out); ww('mix_raw.wav', music_out + sfx_out); ww('nomusic_raw.wav', sfx_out)
if '--report' in sys.argv:
    db = lambda x: 20 * np.log10(rms(x))
    for t0 in np.arange(0, 40, 2.5):
        i, j = int(t0 * SR), int((t0 + 2.5) * SR); print(f'{t0:5.1f}  music {db(music_out[i:j]):6.1f}  sfx {db(sfx_out[i:j]):6.1f}')
mx = np.abs(music_out + sfx_out).max(1); pk_t = sorted(range(0, N, SR // 10), key=lambda i: -mx[i:i + SR // 10].max())[:6]
print('top peaks', [(round(i / SR, 1), round(float(mx[i:i + SR // 10].max()), 2)) for i in pk_t])
