# For every audio cut: loudness of the last 40 ms kept before the cut and the first
# 40 ms kept after it, plus whether the source keeps sounding right after the out point.
import sys, wave, numpy as np
sys.path.insert(0, "."); import edit
wf = wave.open("mix48.wav"); SR = wf.getframerate()
x = np.frombuffer(wf.readframes(wf.getnframes()), np.int16).astype(np.float32) / 32768
def db(t0, t1):
    a = x[int(t0 * SR):int(t1 * SR)]; return 20 * np.log10(np.sqrt((a ** 2).mean() + 1e-12))
for name in sys.argv[1:]:
    shots = edit.audio_runs(name)
    out = 0; print(f"== {name}")
    for i, (a, b) in enumerate(shots):
        nxt = shots[i + 1][0] if i + 1 < len(shots) else None
        out += b - a
        if nxt is not None and abs(nxt - b) < 1e-3: continue
        tail = db(b - 0.04, b); after = db(b, b + 0.06)
        head = db(nxt, nxt + 0.04) if nxt else None; before = db(nxt - 0.06, nxt) if nxt else None
        flag = []
        if after > -32 and after > tail - 3: flag.append("word may continue after OUT")
        if nxt and before > -32 and before > head - 3: flag.append("IN may start mid-word")
        print(f"  out {out:6.2f}s  src {b:.2f}: last40ms {tail:5.1f} dB, dropped-next60ms {after:5.1f} dB"
              + (f" | in {nxt:.2f}: dropped-prev60ms {before:5.1f}, first40ms {head:5.1f}" if nxt else " | END")
              + ("  <-- " + "; ".join(flag) if flag else "  ok"))
