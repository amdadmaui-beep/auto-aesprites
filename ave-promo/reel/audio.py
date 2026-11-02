# AVE "more heat" reel — sound design on the picture cues + Jane Perry voiceover (no background music).
# SFX instruments reused from ../film.
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); FILM = os.path.join(HERE, '..', 'film')
a = open(os.path.join(FILM, 'audio.py')).read(); a = a[:a.index("exec(open(os.path.join(ROOT, 'score_v3.py'))")]
a = a.replace("ROOT = os.path.dirname(os.path.abspath(__file__))", "ROOT = HERE")
exec(a)
b = open(os.path.join(FILM, 'score_v3.py')).read(); exec(b[:b.index('def score_v3():')])
CUTS = [C['card1'], C['card2'], C['card3'], C['card4'], C['white']]
def rv2(p):
    w = wave.open(p); x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768; return x.reshape(-1, w.getnchannels())
# no background music: voice + sound design only
exec(open(os.path.join(HERE, 'sfx2.py')).read())
# voice (Jane Perry): natural speed; only the pause inside line 6 is shortened
def rv(p):
    w = wave.open(p); return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
VOD = os.path.join(HERE, 'vo')
def vline(i, t0, cut=None):
    x = rv(os.path.join(VOD, f'r{i}.wav')); x = hp(x, 90, 2); x = x + .22 * bp(x, 2500, 6500)
    if cut: a0, a1 = int(cut[0] * SR), int(cut[1] * SR); x = np.concatenate([x[:a0], x[a1:]])
    on = np.where(np.abs(x) > .015)[0][0]; x = x[on - int(.01 * SR):]; x[:480] *= np.linspace(0, 1, 480); x[-2400:] *= np.linspace(1, 0, 2400)
    add(vox, t0 - .01, x, 1.0)
vline(1, 0.75); vline(2, 2.70); vline(3, 4.64); vline(4, 6.38); vline(5, 8.25); vline(6, 10.25, (1.03, 1.18)); vline(7, 12.95)
vn = .32 / (np.percentile(np.abs(vox[np.abs(vox).max(1) > 1e-3]).max(1), 99) + 1e-9)
envv = np.abs(vox).max(1); k = int(.03 * SR); envv = np.sqrt(np.convolve(envv ** 2, np.ones(k) / k, 'same'))
act = np.clip(envv / .02, 0, 1); gg = np.zeros_like(act); s_ = 0; ac, rc = np.exp(-1 / (.02 * SR)), np.exp(-1 / (.25 * SR))
for i in range(len(act)):
    v = act[i]; c = ac if v > s_ else rc; s_ = c * s_ + (1 - c) * v; gg[i] = s_
mix = 1.0 * sfx * (1 - .25 * gg)[:, None] + vox * vn
fo = int(.3 * SR); mix[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 1.5
mix = np.tanh(mix * 1.1) / 1.1
os.makedirs(os.path.join(HERE, 'build'), exist_ok=True)
y = np.clip(mix, -1, 1); w = wave.open(os.path.join(HERE, 'build', 'mix_raw.wav'), 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((y * 32767).astype(np.int16).tobytes()); w.close()
# overlap check for the voice lines
print('ok peak', float(np.abs(mix).max()))
if '--report' in sys.argv:
    db = lambda x: 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9)
    for a0 in np.arange(0, 15, 1.25):
        i, j = int(a0 * SR), int((a0 + 1.25) * SR)
        print(f"{a0:5.2f}  music {db(0*music[i:j]+1e-9):6.1f}  sfx {db(.9*sfx[i:j]):6.1f}  voice {db(vox[i:j]*vn):6.1f}")
