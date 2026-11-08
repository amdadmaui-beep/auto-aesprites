# Cursor spec V3: background music = LONOWN "worry" (supplied by the client), SFX from the client's library
# (sfx_library/: the SATISYING bloops + ding, the Premium pack, the UI SaaS pack, the SFX pack) plus synth
# bloops matched to the SATISYING reference. Every cue comes from cues.js, which is locked to the music grid.
# Writes build/music.wav, build/sfx.wav, build/mix_raw.wav, build/nomusic_raw.wav.
import json, re, os, wave, sys
import numpy as np, soundfile as sf
from scipy import signal
from scipy.signal import fftconvolve, resample_poly
HERE = os.path.dirname(os.path.abspath(__file__)); SR = 48000
LIB = os.path.join(HERE, '..', '..', 'sfx_library')
MUSIC = os.environ.get('MUSIC', os.path.join(HERE, 'music', 'LONOWN_worry.wav'))
src = open(os.path.join(HERE, 'cues.js')).read(); body = re.sub(r'//[^\n]*', '', src[src.index('{'):src.rindex('}') + 1])
C = json.loads(re.sub(r'([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:', r'\1"\2":', body))
N = int(C['dur'] * SR); rng = np.random.default_rng(31); B = C['beat']
sfx = np.zeros((N, 2), np.float32); vS = np.zeros((N, 2), np.float32)
def tv(d): return np.arange(int(d * SR)) / SR
def nz(d): return rng.standard_normal(int(d * SR))
def lp(x, f, o=2): b, a = signal.butter(o, min(f, SR / 2 - 100) / (SR / 2), 'low'); return signal.lfilter(b, a, x, axis=0)
def hp(x, f, o=2): b, a = signal.butter(o, f / (SR / 2), 'high'); return signal.lfilter(b, a, x, axis=0)
def bp(x, f1, f2, o=2): b, a = signal.butter(o, [f1 / (SR / 2), min(f2, SR / 2 - 100) / (SR / 2)], 'band'); return signal.lfilter(b, a, x, axis=0)
def osc(f): return np.sin(2 * np.pi * np.cumsum(f) / SR)
def att(t, a=.002): return np.minimum(1, t / a)
def S(t0, x, g=1., pan=0., rv=0.):
    if x.ndim == 1: x = np.stack([x * np.cos((pan + 1) * np.pi / 4), x * np.sin((pan + 1) * np.pi / 4)], 1) * 1.414
    elif pan: x = x * np.array([np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)]) * 1.414
    i = int(round(t0 * SR))
    if i < 0: x = x[-i:]; i = 0
    j = min(N, i + len(x))
    if j <= i: return
    sfx[i:j] += (x[:j - i] * g).astype(np.float32)
    if rv: vS[i:j] += (x[:j - i] * g * rv).astype(np.float32)

# ------------------------------------------------ the client's library
def load(rel):
    x, sr = sf.read(os.path.join(LIB, rel), dtype='float32')
    if x.ndim == 1: x = np.stack([x, x], 1)
    if sr != SR: x = resample_poly(x, SR, sr, axis=0).astype(np.float32)
    return x
def pitch(x, semis):                     # varispeed: pitch and length together, like a tape
    if not semis: return x
    r = 2 ** (semis / 12); n = int(len(x) / r); idx = np.arange(n) * r
    return np.stack([np.interp(idx, np.arange(len(x)), x[:, c]) for c in (0, 1)], 1).astype(np.float32)
BLOOPS = [load(f'satisfying/{f}') for f in sorted(os.listdir(os.path.join(LIB, 'satisfying'))) if f.startswith('bloop_') and f[6:8].isdigit()]
BLOOPS = [b for b in BLOOPS if len(b) > int(.06 * SR)]                     # the full-bodied ones
BURST = load('satisfying/bloop_burst_full.wav'); DING = load('satisfying/ding_confirm.wav')
PREM = {k: load(f'premium_pack/{k}.wav') for k in ['basscrack', 'cine_strike', 'cyber_shift', 'distorting_glitch', 'alienated_warps', 'ripple_texture', 'ripple_texture_2']}
WH = {k: lp(load(f'sfx_pack/{k}.wav'), 7000) for k in ['sfxpack_004.01_whoosh', 'sfxpack_006.40_whoosh', 'sfxpack_007.13_whoosh', 'sfxpack_004.69_whoosh']}
IMP = {k: lp(load(f'sfx_pack/{k}.wav'), 6000) for k in ['sfxpack_003.62_impact', 'sfxpack_006.83_impact', 'sfxpack_009.09_impact']}
UIPOP = [load(f'ui_saas/uisaas_006.{k}_pop.wav') for k in ('36', '48', '61')]; UIWH = lp(load('ui_saas/uisaas_004.15_whoosh.wav'), 6500)
def peak_at(x):                          # the sample index of a sound's loudest moment (to land it on a cue)
    m = np.abs(x).max(1); w = int(.01 * SR); return int(np.argmax(np.convolve(m, np.ones(w) / w, 'same')))
def P_(t0, x, g=1., pan=0., rv=0., land=False):   # place a library sound; land=True puts its peak on t0
    S(t0 - (peak_at(x) / SR if land else 0), x, g, pan, rv)

# ------------------------------------------------ bloops (real + matched synth)
def sbloop(f0=1400, f1=85, tau=.03, dec=.07, drive=1.3, body=.9):
    t = tv(dec * 5); f = f1 + (f0 - f1) * np.exp(-t / tau)
    x = np.tanh(drive * osc(f)) / np.tanh(drive) * np.exp(-t / dec) * att(t, .002)
    x += body * osc(55 + 90 * np.exp(-t / .04)) * np.exp(-t / (dec * 1.3)) * att(t, .004)
    return lp(x, 3200)
k_bl = [0]
def bloop(t0, g=.5, pan=0., semis=0, real=True, f0=None, dec=.07):
    if real:
        b = BLOOPS[k_bl[0] % len(BLOOPS)]; k_bl[0] += 7
        S(t0, pitch(b, semis), g, pan, .1)
    else:
        S(t0, sbloop(f0 or rng.uniform(800, 2000), rng.uniform(75, 110), rng.uniform(.022, .04), dec), g, pan, .1)
def burst(t0, n, span, g=.45, p0=-.6, p1=.6, s0=0, s1=0, shape='swell'):
    # n bloops over `span` seconds, swelling to the middle like the SATISYING reference
    for i in range(n):
        u = i / max(1, n - 1); tt = t0 + span * (u ** 1.15) + rng.uniform(-.006, .006)
        env = (np.sin(np.pi * min(.999, .15 + .85 * u)) ** .6) if shape == 'swell' else 1.0
        bloop(tt, g * (.6 + .4 * env), p0 + (p1 - p0) * u, s0 + (s1 - s0) * u, real=(i % 3 != 2))
def ding(t0, g=.5, semis=0, pan=0.): S(t0, pitch(DING, semis), g, pan, .3)

# ------------------------------------------------ small synth helpers (from V2's creamy kit)
def thock(t0, g=.3, pan=0., deep=1.):
    r = np.random.default_rng(int(t0 * 1e4)); t = tv(.12); f = (165 + 30 * r.random()) * deep
    x = osc(f * (1 + .7 * np.exp(-t / .005))) * np.exp(-t / .022) + .3 * osc(np.full(len(t), f * 3.1)) * np.exp(-t / .01)
    x += .28 * lp(bp(r.standard_normal(len(t)), 900, 3000), 3500) * np.exp(-t / .0025) + .3 * lp(r.standard_normal(len(t)), 420) * np.exp(-t / .01)
    S(t0, lp(x * att(t, .0008), 5000), g * (.85 + .3 * r.random()), pan + (r.random() - .5) * .25, .04)
def sub(t0, g=.5, f0=70, f1=34, dec=.45):
    t = tv(dec * 4); x = osc(f1 + (f0 - f1) * np.exp(-t / .05)) * np.exp(-t / dec) * att(t, .002); S(t0, x, g)
def glide(t0, d, g=.08, f0=400, f1=1200, pan=0.):
    t = tv(d); f = np.geomspace(f0, f1, len(t)); e = np.sin(np.pi * np.minimum(1, t / d)) ** 1.5; S(t0, (osc(f) + .3 * osc(f * 2)) * e, g, pan, .4)
def swish(t0, d=.3, g=.25, f0=300, f1=2000, p0=-.5, p1=.5):
    t = tv(d); x = nz(d); y = np.zeros_like(x); seg = 384
    for i in range(0, len(x), seg):
        fc = f0 * (f1 / f0) ** (i / len(x)); y[i:i + seg] = bp(x[max(0, i - 1024):i + seg], fc / 1.6, min(fc * 1.6, 8000))[-len(x[i:i + seg]):]
    y = lp(y, 3500) * 2; e = np.sin(np.pi * t / d) ** 2; pn = np.linspace(p0, p1, len(t))
    S(t0, np.stack([y * e * np.cos((pn + 1) * np.pi / 4), y * e * np.sin((pn + 1) * np.pi / 4)], 1) * 1.41, g, 0, .15)

# ================================================= cues: ONE sound per real change on screen (the music carries the rest)
# intro: the song's own hits (0.139, 0.578) ARE the title smashes; we only add weight, no extra events
thock(C['cmdk'], .5, 0, .75); bloop(C['cmdk'] + .01, .55, 0, -3)                         # ⌘K, on the 808
P_(C['sh2'] - .05, WH['sfxpack_006.40_whoosh'], .3, -.3)                               # code fragments fly in
bloop(C['lock0'], .6, 0, 0)                                                            # …and lock, on the 808
P_(C['ember'], PREM['alienated_warps'], .45, 0, .2, land=True)                         # the rush collapses into the ember
P_(C['sh5'], PREM['basscrack'], .8, 0, .2, land=True)                                  # DROP 1: detonation → cube
P_(C['sh6'] - .05, WH['sfxpack_004.01_whoosh'], .35, -.4)                              # camera orbit
bloop(C['icon'], .45, .2, 4)                                                           # icon lands
P_(C['meet'], IMP['sfxpack_009.09_impact'], .55, 0, .1, land=True)                    # MEET CURSOR.
P_(C['ghost'], PREM['ripple_texture_2'], .25, .25, .3)                                 # ghost suggestion
thock(C['tab'], .6, 0, .62); ding(C['tab'] + .04, .45, -2)                             # THE Tab
bloop(C['back'] + .2, .45, .2, -2)                                                     # …and snap home
swish(C['select'], .22, .18, 500, 1500, -.2, .3)                                       # selection
burst(C['more'] + .18, 8, .42, .42, -.6, .6, -2, 5)                         # MORE BUILDING.: one signature burst, one letter each
P_(C['sh13'] - .08, WH['sfxpack_004.01_whoosh'], .28, .3)                              # prompt box
bloop(C['send'], .7, .35, -2); P_(C['send'], PREM['cine_strike'], .4, 0, .15, land=True)  # send, on DROP 2
P_(C['fan'] - .05, WH['sfxpack_006.40_whoosh'], .3, -.5)                               # files fan out
for i, c in enumerate(['d1', 'd2', 'd3', 'd4']): bloop(C[c] + .22, .4, .3 - .2 * i, i - 1)   # each file's diff lands
P_(C['sh16'] - .05, UIWH, .25, 0)                                                      # split screen
ding(C['ready'], .5, 0, .3)                                                            # ✓ Ready
for i, a_ in enumerate(['a1', 'a2', 'a3']): bloop(C[a_] + .2, .42, .5, i * 2)            # code becomes components
P_(C['sh19'], PREM['basscrack'], .7, 0, .2, land=True)                                 # explode
for i in range(0, 7, 2): bloop(C['r0'] + i * C['rStep'] + .2, .38, [-.5, -.6, -.2, .2, .6, -.3, .4][i], -3 + i)   # each part snaps home, on the 8ths
thock(C['export'], .4, .4, .75)                                                        # export
P_(C['sh21'] - .05, WH['sfxpack_004.69_whoosh'], .25, 0, .15)                          # pull back into the editor
P_(C['toc'], PREM['cine_strike'], .55, 0, .15, land=True)                              # TO CREATION. on DROP 3
P_(C['ag0'] - .05, WH['sfxpack_004.01_whoosh'], .35, 0)                              # three agents fly in
for i, c in enumerate(['ckA', 'ckB', 'ckC']): bloop(C[c], .5, [-.5, 0, .5][i], [0, 2, 4][i])   # each one ticks Done, on the beat
ding(C['ckC'] + .03, .4, 2)                                                            # 3 of 3 done
swish(C['fold'], .3, .18, 400, 1200, .3, -.3)                                          # they fold into one
P_(C['black'], PREM['alienated_warps'], .4, 0, .1, land=True)                         # the cube collapses to the ember
P_(C['sh23'], PREM['cine_strike'], .5, 0, .25, land=True); ding(C['sh23'] + .06, .45, -3)   # lockup on the song's final 808

# ================================================= music bed
mus, msr = sf.read(MUSIC, dtype='float32')
if mus.ndim == 1: mus = np.stack([mus, mus], 1)
if msr != SR: mus = resample_poly(mus, SR, msr, axis=0).astype(np.float32)
# arrangement: the song plays from its top to the bar line at C.black, then jumps to the song's own final bar
# (its 2-beat break + last 808 hit), so the lockup lands on the real ending instead of a fade
a_end = int(C['songEnd'] * SR); i0 = int(C['black'] * SR); xf = int(.012 * SR)
tail = mus[a_end:]; head = mus[:i0 + xf].copy()
music = np.zeros((N, 2), np.float32); music[:i0 + xf] = head[:N]
w = np.linspace(0, 1, xf)[:, None]; music[i0:i0 + xf] = head[i0:i0 + xf] * (1 - w) + tail[:xf] * w
n_t = min(len(tail) - xf, N - i0 - xf); music[i0 + xf:i0 + xf + n_t] = tail[xf:xf + n_t]
print('song end lands at', round(C['black'] + (70.2 - C['songEnd']), 3), 's (lockup', C['sh23'], ')')
# duck the bed under the sound design (up to 4.5 dB), so every bloop reads on top of the song
def env(x, att_s=.004, rel_s=.12):
    m = np.abs(x).max(1); a = np.exp(-1 / (att_s * SR)); r = np.exp(-1 / (rel_s * SR)); e = np.empty_like(m); c = 0.
    for k in range(len(m)): v = m[k]; c = a * c + (1 - a) * v if v > c else r * c + (1 - r) * v; e[k] = c
    return e
def room(x, dec=.28, length=1.2, seed=5):
    r = np.random.default_rng(seed); t = tv(length); ir = r.standard_normal(len(t)) * np.exp(-t / dec); ir = lp(ir, 5000); ir /= np.sqrt((ir ** 2).sum())
    return np.stack([fftconvolve(x[:, c], np.roll(ir, 17 * c), 'full')[:N] for c in (0, 1)], 1).astype(np.float32)
sfx_out = sfx + room(vS) * .28
# silence means silence: nothing but the tail of the suction in the blackout beat
def rms(x): return float(np.sqrt(np.mean(x ** 2)) + 1e-9)
MUS_LVL = 10 ** (-20.5 / 20) / rms(music[:int(C['black'] * SR)])      # the bed sits around −20.5 dBFS RMS
music *= MUS_LVL
e = env(sfx_out); dk = 1 - .25 * np.clip(e / (np.percentile(e, 99.5) + 1e-9), 0, 1); music *= dk[:, None]
SFX_LVL = 1.0
sfx_out *= SFX_LVL
def limiter_gain(x, thr=.89, look=.003, rel=.09):
    L = int(look * SR); m = np.abs(x).max(1); req = np.minimum(1, thr / (m + 1e-9))
    req = np.pad(req, (0, L), constant_values=1); req = np.lib.stride_tricks.sliding_window_view(req, L + 1).min(1)[:len(m)]
    g = np.empty_like(req); a = np.exp(-1 / (L / 2 + 1)); r = np.exp(-1 / (rel * SR)); cur = 1.
    for k in range(len(req)):
        tgt = req[k]; cur = a * cur + (1 - a) * tgt if tgt < cur else r * cur + (1 - r) * tgt; g[k] = cur
    return np.minimum(g, req).astype(np.float32)
# bring the whole mix to a healthy body, then catch the peaks (one clean gain curve, no waveshaping)
mix = music + sfx_out; pre = 10 ** (-16.5 / 20) / rms(mix[:int(C['black'] * SR)]); music *= pre; sfx_out *= pre
gl = limiter_gain(music + sfx_out); music *= gl[:, None]; sfx_out *= gl[:, None]
print('pre', round(pre, 2), 'max GR dB', round(20 * np.log10(gl.min()), 1))
def ww(name, x):
    y = np.clip(x, -1, 1); w = wave.open(os.path.join(HERE, 'build', name), 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((y * 32767).astype(np.int16).tobytes()); w.close()
os.makedirs(os.path.join(HERE, 'build'), exist_ok=True)
ww('music.wav', music); ww('sfx.wav', sfx_out); ww('mix_raw.wav', music + sfx_out)
sl = limiter_gain(sfx_out / (np.abs(sfx_out).max() + 1e-9) * 1.6); ww('nomusic_raw.wav', sfx_out / (np.abs(sfx_out).max() + 1e-9) * 1.6 * sl[:, None])
if '--report' in sys.argv:
    db = lambda x: 20 * np.log10(rms(x))
    for t0 in np.arange(0, 40, 2.0):
        i, j = int(t0 * SR), int((t0 + 2) * SR); print(f'{t0:5.1f}  music {db(music[i:j]):6.1f}  sfx {db(sfx_out[i:j]):6.1f}')
