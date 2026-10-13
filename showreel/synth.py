"""Synthesizes the score + SFX for the reel (120 BPM, 25 s) and measures beats.json from the kick stem.

    python3 synth.py            -> build/score_raw.wav, beats.json
"""
import json, os, wave
import numpy as np

SR = 48000
DUR = 25.0
N = int(SR * DUR)
BPM = 120
BEAT = 60 / BPM
ROOT = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(ROOT, 'build'), exist_ok=True)
rng = np.random.default_rng(7)


def T(d):
    return np.arange(int(d * SR)) / SR


class Bus:
    def __init__(self):
        self.L = np.zeros(N)
        self.R = np.zeros(N)

    def add(self, t0, sig, gain=1.0, pan=0.0):
        i = int(round(t0 * SR))
        if i >= N:
            return
        if i < 0:
            sig = sig[-i:]
            i = 0
        sig = sig[: N - i]
        gl, gr = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        self.L[i:i + len(sig)] += sig * gain * gl * 1.4142
        self.R[i:i + len(sig)] += sig * gain * gr * 1.4142

    def scale(self, env):
        self.L *= env
        self.R *= env


def fft_filter(x, lo=None, hi=None, order=2):
    n = len(x)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    h = np.ones_like(f)
    if hi:
        h /= np.sqrt(1 + (f / hi) ** (2 * order))
    if lo:
        h /= np.sqrt(1 + (lo / np.maximum(f, 1e-3)) ** (2 * order))
    return np.fft.irfft(X * h, n)


def sweep_filter(x, fc_fn, bw_oct=0.8, n=2048, hop=512):
    """time-varying band-pass via STFT; fc_fn(t) -> centre frequency at time t (s from start of x)"""
    win = np.hanning(n)
    pad = np.concatenate([np.zeros(n), x, np.zeros(n)])
    out = np.zeros_like(pad)
    ws = np.zeros_like(pad)
    fr = np.maximum(np.fft.rfftfreq(n, 1 / SR), 1)
    for s in range(0, len(pad) - n, hop):
        tc = (s + n / 2 - n) / SR
        mask = np.exp(-0.5 * (np.log2(fr / fc_fn(tc)) / bw_oct) ** 2)
        out[s:s + n] += np.fft.irfft(np.fft.rfft(pad[s:s + n] * win) * mask, n) * win
        ws[s:s + n] += win ** 2
    return (out / np.maximum(ws, 1e-6))[n:n + len(x)]


def saw(freq, d, kmax=40, detune=0.0, phase=0.0):
    t = T(d)
    f = freq * 2 ** (detune / 1200)
    K = int(max(1, min(kmax, 15000 // f)))
    y = np.zeros_like(t)
    for k in range(1, K + 1):
        y += np.sin(2 * np.pi * k * f * t + phase * k) / k
    return y * 0.6


def env_ad(d, a=0.003, dec=0.2):
    t = T(d)
    return np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / dec)


def noise(d):
    return rng.standard_normal(int(d * SR))


NOTE = lambda n: 440 * 2 ** ((n - 69) / 12)

# ---------------------------------------------------------------- instruments

def kick(gain=1.0):
    t = T(0.5)
    f = 46 + 120 * np.exp(-t / 0.032)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t / 0.26)
    click = fft_filter(noise(0.5), lo=2500) * np.exp(-t / 0.003) * 0.35
    return np.tanh(1.6 * (body + click)) * gain


def clap():
    d = 0.4
    t = T(d)
    n = fft_filter(noise(d), lo=900, hi=5200)
    env = np.zeros_like(t)
    for o in (0, 0.009, 0.019):
        env += (t >= o) * np.exp(-np.maximum(t - o, 0) / (0.012 if o < 0.019 else 0.11))
    return n * env * 0.5


def hat(open_=False):
    d = 0.25 if open_ else 0.08
    return fft_filter(noise(d), lo=7500) * env_ad(d, 0.001, 0.09 if open_ else 0.022) * 0.4


def bass_note(freq, d):
    s = saw(freq, d, kmax=24) * 0.6 + np.sin(2 * np.pi * freq * T(d)) * 0.8
    s = fft_filter(s, hi=520)
    return s * env_ad(d, 0.004, 0.16) * 0.9


def stab(freqs, d=0.5, dec=0.22, hi=3200):
    s = sum(saw(f, d, detune=dt) for f in freqs for dt in (-9, 9))
    return fft_filter(s, hi=hi) * env_ad(d, 0.002, dec) * 0.22


def pad(freqs, d):
    s = sum(saw(f, d, kmax=26, detune=dt, phase=i) for i, f in enumerate(freqs) for dt in (-7, 0, 7))
    t = T(d)
    e = np.minimum(1, t / 0.06) * np.minimum(1, (d - t) / 0.08)
    return fft_filter(s, hi=1500) * e * 0.06


def pluck(freq, d=0.22):
    return fft_filter(saw(freq, d, kmax=30), hi=3600) * env_ad(d, 0.001, 0.07) * 0.25


def impact(size=1.0):
    d = 2.2
    t = T(d)
    f = 38 + 90 * np.exp(-t / 0.08)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / (0.5 * size))
    crack = fft_filter(noise(d), lo=200, hi=6000) * np.exp(-t / (0.07 * size)) * 0.6
    return np.tanh(1.3 * (boom + crack)) * size


def whoosh(d, f0, f1, peak=0.65):
    x = noise(d)
    y = sweep_filter(x, lambda tt: f0 * (f1 / f0) ** np.clip(tt / d, 0, 1), bw_oct=0.9)
    t = T(d)
    u = t / d
    env = np.where(u < peak, (u / peak) ** 2, ((1 - u) / (1 - peak)) ** 1.4)
    return y * env * 1.4


def bloop(f0=900, f1=260, d=0.18):
    t = T(d)
    f = f1 + (f0 - f1) * np.exp(-t / 0.025)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env_ad(d, 0.001, 0.06) * 0.55


def tick(f=3200, d=0.012, g=0.25):
    t = T(d)
    return (np.sin(2 * np.pi * f * t) * 0.6 + fft_filter(noise(d), lo=3000) * 0.4) * np.exp(-t / 0.003) * g


def thock():
    t = T(0.08)
    return np.sin(2 * np.pi * (520 + 300 * np.exp(-t / 0.01)) * t) * np.exp(-t / 0.02) * 0.6


def reverb(x, secs=1.8, decay=0.5, seed=1):
    r = np.random.default_rng(seed)
    t = T(secs)
    ir = r.standard_normal(len(t)) * np.exp(-t / decay)
    ir = fft_filter(ir, hi=6000)
    ir /= np.sqrt(np.sum(ir ** 2))
    L = len(x) + len(ir)
    y = np.fft.irfft(np.fft.rfft(x, L) * np.fft.rfft(ir, L), L)[: len(x)]
    return y

# ---------------------------------------------------------------- arrangement

kick_bus, drums, music, sfx, send = Bus(), Bus(), Bus(), Bus(), Bus()

beats = [i * BEAT for i in range(50)]
CH = {  # chords per 2 s bar: (bass midi, pad midis)
    'Dm': (38, [62, 65, 69]), 'Bb': (34, [58, 62, 65]), 'F': (41, [57, 60, 65]), 'C': (36, [55, 60, 64]),
}
PROG = ['Dm', 'Bb', 'F', 'C']


def chord_at(t):
    if t >= 21.0:
        return 'Dm'
    if t >= 20.0:
        return 'C'
    return PROG[int(t // 2) % 4]

# kick: four on the floor, out for the 20-21 riser, back on the drop, last hit at 24
kick_times = [b for b in beats if b < 20.0] + [21.0, 21.5, 22.0, 22.5, 23.0, 23.5, 24.0]
for b in kick_times:
    kick_bus.add(b, kick(1.15 if b in (0.0, 21.0, 24.0) else 1.0))

# clap on 2 and 4
for b in beats:
    if 2.0 <= b < 20.0 and int(round(b / BEAT)) % 2 == 1:
        c = clap()
        drums.add(b, c, 0.8)
        send.add(b, c, 0.35)
for b in (21.5, 22.5, 23.5):
    drums.add(b, clap(), 0.7)
    send.add(b, clap(), 0.3)

# hats
for i in range(200):
    t = i * BEAT / 4
    if t >= 20.0 and t < 21.0 or t >= 24.0:
        continue
    off8 = i % 4 == 2
    if t < 4.0 or t >= 21.0:
        if off8:
            drums.add(t, hat(open_=True), 0.45, 0.3)
        continue
    drums.add(t, hat(open_=off8), 0.55 if off8 else 0.28 + 0.1 * (i % 2 == 0), 0.25 if i % 2 else -0.2)

# snare fills into 8.5 and accelerating roll into the 21 drop
for k in range(4):
    drums.add(8.0 + k * 0.125, clap(), 0.35 + 0.1 * k, -0.2)
t = 20.0
k = 0
while t < 20.98:
    drums.add(t, clap(), 0.18 + 0.55 * (t - 20.0), 0.15 * ((k % 2) * 2 - 1))
    step = 0.125 if t < 20.5 else 0.0625 if t < 20.75 else 0.03125
    t += step
    k += 1

# bass: driving 8ths with octave pops
for i in range(50):
    t = i * BEAT / 2 + 2.0
    if t >= 20.0 and t < 21.0 or t >= 24.0 or t >= 25.0:
        continue
    root = CH[chord_at(t)][0]
    n = root + (12 if i % 4 == 3 else 0)
    music.add(t, bass_note(NOTE(n), 0.24), 0.9)

# pads per bar
for bar in range(13):
    t0 = bar * 2.0
    if t0 >= 24.0:
        break
    name = chord_at(t0)
    d = 2.0 if t0 < 20 else 1.0
    if t0 == 20.0:
        d = 1.0
    music.add(t0, pad([NOTE(n) for n in CH[name][1]], d), 1.0, 0)
    send.add(t0, pad([NOTE(n) for n in CH[name][1]], d), 0.5)
    if t0 == 20.0:
        music.add(21.0, pad([NOTE(n) for n in CH['Dm'][1]], 3.0), 1.0)
        send.add(21.0, pad([NOTE(n) for n in CH['Dm'][1]], 3.0), 0.5)
        break

# hook stabs on each word, plus the drop and the final hit
for t0 in (0.0, 0.5, 1.0, 1.5, 21.0, 24.0):
    nm = 'Dm'
    s = stab([NOTE(n + 12) for n in CH[nm][1]] + [NOTE(CH[nm][0] + 24)], d=0.9 if t0 >= 21 else 0.45,
             dec=0.5 if t0 >= 21 else 0.18)
    music.add(t0, s, 1.1)
    send.add(t0, s, 0.6)

# arp: 16ths 8.5 -> 20, softer 21 -> 24
pat = [0, 1, 2, 1, 2, 0, 2, 1]
for i in range(400):
    t = 8.5 + i * BEAT / 4
    if t >= 24.0:
        break
    if 20.0 <= t < 21.0:
        continue
    tones = CH[chord_at(t)][1]
    n = tones[pat[i % 8]] + 12
    g = 0.55 if t < 20 else 0.35
    p = pluck(NOTE(n))
    music.add(t, p, g, 0.4 if i % 2 else -0.4)
    send.add(t, p, g * 0.5)

# ---- sfx (snapped to the film's cue times) ----
for t0, size in ((0.0, 0.8), (4.0, 0.55), (6.5, 0.45), (8.5, 0.6), (12.5, 0.5), (14.5, 0.4), (16.5, 0.55), (21.0, 1.25), (24.0, 1.1)):
    im = impact(size)
    sfx.add(t0, im, 0.7)
    send.add(t0, im, 0.25)
for t0, d, f0, f1, g in (
        (1.88, 0.2, 400, 2500, 0.25),     # ball launch
        (3.85, 0.3, 300, 4000, 0.5),      # iris
        (6.15, 0.35, 5000, 400, 0.45),    # slats down
        (8.2, 0.3, 4000, 600, 0.35),      # collapse to baselines
        (10.25, 0.42, 300, 6000, 0.8),    # whip
        (12.0, 0.5, 300, 5000, 0.6),      # card fly-through
        (14.15, 0.35, 3000, 500, 0.35),   # straighten
        (16.15, 0.35, 5000, 400, 0.45),   # slats down
        (17.9, 0.75, 6000, 300, 0.6),     # zoom out
        (18.95, 0.3, 800, 3000, 0.3), (19.45, 0.3, 800, 3000, 0.3), (19.95, 0.3, 800, 3000, 0.3),  # shuffles
        (21.0, 0.5, 6000, 300, 0.5),      # iris closes
        (23.45, 0.55, 500, 3500, 0.35),   # final hop
):
    sfx.add(t0, whoosh(d, f0, f1), g, 0.0)
# riser into the drop
rd = 1.95
rt = T(rd)
riser = sweep_filter(noise(rd), lambda tt: 300 * (9000 / 300) ** np.clip(tt / rd, 0, 1), bw_oct=0.6) * (rt / rd) ** 2 * 1.6
gl = 180 * 4 ** (rt / rd)
riser += np.sin(2 * np.pi * np.cumsum(gl) / SR) * 0.08 * (rt / rd) ** 1.5
sfx.add(19.05, riser, 0.8)
send.add(19.05, riser, 0.3)
# ball bloops
for t0, f0 in ((2.5, 900), (3.0, 820), (3.5, 760), (4.0, 700), (24.0, 1000)):
    sfx.add(t0, bloop(f0), 0.8, 0.2)
# morph blips
for t0 in (7.0, 7.5, 8.0):
    sfx.add(t0, bloop(1400, 700, 0.1), 0.35, -0.3)
# card steps
for t0 in (11.0, 11.5, 12.0):
    sfx.add(t0, thock(), 0.7)
# odometer ticks, slowing like the digits
tt = 14.5
while tt < 15.4:
    sfx.add(tt, tick(2600, g=0.18), 1.0, 0.3)
    tt += 0.02 + 0.12 * ((tt - 14.5) / 0.9) ** 2
# tile rotations
for t0 in np.arange(17.0, 20.0, 0.5):
    sfx.add(t0 + 0.05, tick(1800, 0.02, 0.2), 1.0, -0.3)
# mosaic flips
for i in range(9):
    sfx.add(20.3 + i * 0.065, tick(1200 + 120 * i, 0.03, 0.25), 1.0, (i % 3 - 1) * 0.5)
# typing (labels and credits) — quiet, under the music
TYPING = [(0.12, 6, 30), (0.32, 29, 70), (2.2, 45, 48), (4.35, 40, 48), (6.7, 33, 48), (8.8, 46, 48), (10.75, 34, 48),
          (12.7, 30, 48), (14.9, 36, 48), (16.7, 33, 48), (21.75, 30, 44), (22.45, 53, 56), (23.05, 70, 64)]
for t0, n, cps in TYPING:
    for c in range(0, n, 2):
        sfx.add(t0 + c / cps, tick(3800 + 400 * ((c * 7) % 3), 0.008, 0.11), 1.0, 0.35)

# ---------------------------------------------------------------- mix

tt = np.arange(N) / SR
duck = np.ones(N)
for b in kick_times:
    m = tt >= b
    duck[m] = np.minimum(duck[m], 1 - 0.65 * np.exp(-(tt[m] - b) / 0.11))
music.scale(duck)
send.L *= duck
send.R *= duck

wetL = reverb(send.L, seed=1)
wetR = reverb(send.R, seed=2)
L = kick_bus.L * 0.95 + drums.L * 0.8 + music.L * 0.9 + sfx.L * 0.85 + wetL * 0.55
R = kick_bus.R * 0.95 + drums.R * 0.8 + music.R * 0.9 + sfx.R * 0.85 + wetR * 0.55
# master: gentle glue + tail fade over the last 0.3 s
L = np.tanh(L * 0.8)
R = np.tanh(R * 0.8)
fade = np.clip((DUR - tt) / 0.3, 0, 1)
L *= fade
R *= fade
pk = max(np.abs(L).max(), np.abs(R).max())
L, R = L / pk * 0.89, R / pk * 0.89


def write_wav(path, L, R):
    data = (np.stack([L, R], 1) * 32767).astype(np.int16)
    with wave.open(path, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


write_wav(os.path.join(ROOT, 'build', 'score_raw.wav'), L, R)

# ---------------------------------------------------------------- measure beats from the kick stem
k = kick_bus.L + kick_bus.R
hop = 240  # 5 ms
env = np.array([np.sum(k[i:i + hop] ** 2) for i in range(0, N - hop, hop)])
flux = np.maximum(np.diff(env, prepend=0), 0)
thr = flux.max() * 0.2
onsets = []
for i in range(0, len(flux) - 1):
    if flux[i] > thr and (i == 0 or flux[i] >= flux[i - 1]) and flux[i] >= flux[i + 1]:
        tsec = i * hop / SR
        if not onsets or tsec - onsets[-1] > 0.4:
            onsets.append(tsec)
onsets = np.array(onsets)
ioi = np.median(np.diff(onsets))
bpm = 60 / ioi
period = 60 / round(bpm)
phase = float(np.median(onsets % period))
if phase > period / 2:
    phase -= period
grid = [round(phase + i * period, 4) for i in range(int(DUR / period) + 1) if 0 <= phase + i * period < DUR]
grid = [max(0.0, g) for g in grid]
json.dump({
    'bpm': round(bpm, 2),
    'beats': grid,
    'downbeats': grid[::4],
    'measured_onsets': [round(float(o), 4) for o in onsets],
}, open(os.path.join(ROOT, 'beats.json'), 'w'), indent=1)
print(f'bpm {bpm:.2f}  phase {phase*1000:.1f} ms  onsets {len(onsets)}  grid {len(grid)}')
