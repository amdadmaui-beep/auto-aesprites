# Slice a (foreground) audio file into individual sound effects and classify each one.
# usage: extract.py <in.wav> <src-label> <outdir> [thresh_db_below_peak] [highpass_hz]
import sys, os, json, numpy as np, soundfile as sf, librosa
from scipy import signal
inp, lab, out = sys.argv[1:4]; th = float(sys.argv[4]) if len(sys.argv) > 4 else 30; hpf = float(sys.argv[5]) if len(sys.argv) > 5 else 0
y, sr = sf.read(inp); y = y if y.ndim == 2 else np.stack([y, y], 1)
if hpf: b, a = signal.butter(2, hpf / (sr / 2), 'high'); y = signal.filtfilt(b, a, y, axis=0)
m = np.abs(y).max(1); w = int(.012 * sr); env = np.sqrt(np.convolve(m ** 2, np.ones(w) / w, 'same')); edb = 20 * np.log10(env + 1e-9)
floor = np.percentile(edb, 20); top = edb.max(); thr = max(floor + 10, top - th)
LOCAL = os.environ.get('LOCAL')
if LOCAL:   # busy beds: an event must stand out from its own surroundings (rolling 1.5 s median) by LOCAL dB
    from scipy.ndimage import median_filter
    dec = 48; ed = edb[::dec]; med = np.repeat(median_filter(ed, size=int(1.5 * sr / dec)), dec)[:len(edb)]
    on = (edb > med + float(LOCAL)) & (edb > top - th)
else:
    on = edb > thr
segs = []; st = None
for i in range(len(on)):
    if on[i] and st is None: st = i
    if not on[i] and st is not None: segs.append([st, i]); st = None
if st is not None: segs.append([st, len(on)])
merged = []
for s in segs:                                   # merge gaps under 50 ms
    if merged and s[0] - merged[-1][1] < .05 * sr: merged[-1][1] = s[1]
    else: merged.append(s)
os.makedirs(out, exist_ok=True); rows = []
GRID = os.environ.get('GRID')      # "period,offset": drop tiny clicks that sit on the music's hi-hat grid (bed leakage)
if GRID:
    P, O = map(float, GRID.split(','))
    def on_grid(t): return abs(((t - O + P / 2) % P) - P / 2) < .03
    merged = [m for m in merged if not ((m[1] - m[0]) / sr < .1 and on_grid(m[0] / sr))]
starts = [m[0] for m in merged] + [len(edb)]
for k, (s0, s1) in enumerate(merged):
    if (s1 - s0) / sr < .025: continue
    a = max(0, s0 - int(.02 * sr)); pk = s0 + int(np.argmax(env[s0:s1])); pkdb = edb[pk]
    e = s1                                        # extend the tail until 35 dB under the peak or 1.5 s
    lim = (.6 if LOCAL else 1.5) * sr
    while e < len(edb) - 1 and edb[e] > pkdb - 35 and e - s1 < lim and e < starts[k + 1] - int(.005 * sr) and (not LOCAL or edb[e] > med[e] + 2): e += 1
    x = y[a:e].copy(); n = len(x); fo = min(int(.03 * sr), n // 4); x[-fo:] *= np.linspace(1, 0, fo)[:, None]; x[:int(.003 * sr)] *= np.linspace(0, 1, int(.003 * sr))[:, None]
    mono = x.mean(1); dur = n / sr
    S = np.abs(librosa.stft(mono, n_fft=1024, hop_length=256)) + 1e-9; f = librosa.fft_frequencies(sr=sr, n_fft=1024)
    cent = float((S.mean(1) * f).sum() / S.mean(1).sum()); flat = float(np.exp(np.log(S).mean(0)).mean() / S.mean())
    low = float(S[f < 150].sum() / S.sum()); att = (pk - a) / sr
    if low > .35 and att < .06: cls = 'impact'
    elif dur > .3 and att > .12 and flat > .05: cls = 'riser' if att / dur > .65 else 'whoosh'
    elif dur > .3 and att > .12: cls = 'swell'
    elif flat < .02 and cent > 600: cls = 'ping' if dur > .12 else 'blip'
    elif dur < .14 and cent > 1500: cls = 'click'
    elif dur < .2: cls = 'pop'
    elif dur > 1.2: cls = 'sequence'
    else: cls = 'hit'
    x = x / (np.abs(x).max() + 1e-9) * .89
    fn = f'{lab}_{a / sr:06.2f}_{cls}.wav'; sf.write(os.path.join(out, fn), x.astype(np.float32), sr)
    rows.append(dict(file=fn, t=round(a / sr, 3), dur=round(dur, 3), cls=cls, peak_db=round(float(pkdb), 1), centroid=int(cent), flatness=round(flat, 3), attack=round(att, 3)))
json.dump(rows, open(os.path.join(out, lab + '_index.json'), 'w'), indent=1)
from collections import Counter; print(lab, len(rows), 'sfx', dict(Counter(r['cls'] for r in rows)), 'thr', round(thr - top, 1))
