# Cut the two takes into phrases and place each where the reference narrator says the matching line.
# Needs take1.wav / take2.wav: ffmpeg -i take1.mp3 -ar 48000 -ac 1 take1.wav (same for take2).
import json, numpy as np, soundfile as sf
t1, sr = sf.read('take1.wav'); t2, _ = sf.read('take2.wav')
W1 = json.load(open('words_raw.json')); W2 = json.load(open('words2.json'))
def span(W, first, last, occ=0):
    idx = [i for i, w in enumerate(W) if w[0].lower().strip('.,?') == first]; i0 = idx[occ]
    i1 = next(i for i in range(i0, len(W)) if W[i][0].lower().strip('.,?') == last)
    return W[i0][1], W[i1][2], W[i0:i1 + 1]
P = [  # take, first word, last word, occurrence, place at (s)
 (1, 'every', 'before', 0, 2.54), (1, 'something', 'new', 1, 6.52), (1, 'something', 'out', 2, 7.82),
 (1, 'you', 'right', 0, 9.88), (1, 'but', 'simple', 0, 11.50), (1, "that's", 'in', 0, 14.16),
 (1, 'your', 'tasks', 0, 16.26), (1, 'want', 'pizza', 1, 20.34), (1, 'perplexity', 'down', 1, 22.90),
 (1, 'ingredients', 'it', 0, 24.84), (2, 'whatever', 'you', 0, 27.2), (1, 'got', 'up', 0, 30.45),
 (1, 'it', 'clearly', 3, 31.85), (2, 'perplexity', 'do', 1, 36.3), (1, 'learn', 'done', 0, 38.64),
 (1, 'perplexity', 'today', 2, 41.4)]
DUR = 44.5; out = np.zeros(int(DUR * sr)); words = []
for take, a, b, occ, at in P:
    src, W = (t1, W1) if take == 1 else (t2, W2)
    s, e, ws = span(W, a, b, occ)
    s0, e0 = max(0, s - .06), e + .22
    seg = src[int(s0 * sr):int(e0 * sr)].copy()
    f = int(.012 * sr); seg[:f] *= np.linspace(0, 1, f); seg[-f*3:] *= np.linspace(1, 0, f*3)
    i = int((at - .06) * sr); out[i:i + len(seg)] += seg
    for w in ws: words.append([w[0], round(at + w[1] - s, 2), round(at + w[2] - s, 2)])
sf.write('vo_placed.wav', out, sr); json.dump(words, open('words_placed.json', 'w'))
print(' '.join(f'{w}@{t}' for w, t, _ in words))
