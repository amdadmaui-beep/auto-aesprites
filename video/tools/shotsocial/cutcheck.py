# Loudness envelope around every audio cut of a reel, from the original mic tracks.
import json, sys, wave, numpy as np
sys.path.insert(0, ".")
import edit
wf = wave.open("mix48.wav"); SR = wf.getframerate()
x = np.frombuffer(wf.readframes(wf.getnframes()), np.int16).astype(np.float32) / 32768
HOP = int(SR * 0.01)
def rms_db(t0, t1):
    a = x[int(t0 * SR):int(t1 * SR)]
    n = len(a) // HOP
    r = np.sqrt((a[:n * HOP].reshape(n, HOP) ** 2).mean(1) + 1e-12)
    return 20 * np.log10(r)
name = sys.argv[1]
shots = [(edit.snap(a), edit.snap(b)) for a, b, *_ in edit.CLIPS[name]]
lo, hi = shots[0][0], shots[-1][1]
env = rms_db(lo, hi)
floor = np.percentile(env, 10); speech = np.percentile(env, 70)
print(f"{name}: noise floor {floor:.1f} dB, speech {speech:.1f} dB")
out_t = 0
for i in range(len(shots) - 1):
    a, b = shots[i]; c, d = shots[i + 1]
    out_t += b - a
    if abs(c - b) < 1e-3:
        continue
    e_out = rms_db(b - 0.15, b + 0.35); e_in = rms_db(c - 0.35, c + 0.15)
    fmt = lambda e: " ".join(f"{v:4.0f}" for v in e)
    print(f"\ncut @ out {out_t:6.2f}s  | src out {b:.2f} -> in {c:.2f}")
    print("  OUT -0.15..+0.35:", fmt(e_out))
    print("  IN  -0.35..+0.15:", fmt(e_in))
