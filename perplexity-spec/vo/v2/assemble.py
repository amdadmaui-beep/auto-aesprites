# Emotional V2 VO: cut the two takes (p1, p2) into phrases and place each where the reference narrator speaks.
# Needs p1.wav / p2.wav: ffmpeg -i p1.mp3 -ar 48000 -ac 1 p1.wav (same for p2).
import json, numpy as np, soundfile as sf
T = {1: sf.read('p1.wav'), 2: sf.read('p2.wav')}; sr = T[1][1]
W = {1: json.load(open('p1_words.json')), 2: json.load(open('p2_words.json'))}
norm = lambda s: s.lower().strip('.,?!')
def span(Wt, first, last, occ=0):
    i0 = [i for i, w in enumerate(Wt) if norm(w[0]) == first][occ]
    i1 = next(i for i in range(i0, len(Wt)) if norm(Wt[i][0]) == last)
    return Wt[i0][1], Wt[i1][2], Wt[i0:i1 + 1]
P = [(1, 'every', 'before', 0, 2.54), (1, 'something', 'new', 1, 6.52), (1, 'something', 'out', 2, 7.82),
     (1, 'you', 'right', 0, 10.0), (1, 'but', 'simple', 0, 12.0), (1, "that's", 'in', 0, 14.75),
     (1, 'your', 'tasks', 0, 17.05), (2, 'want', 'pizza', 0, 20.34), (2, 'perplexity', 'down', 0, 22.9),
     (2, 'ingredients', 'it', 0, 24.85), (2, 'whatever', 'you', 0, 27.45), (2, 'got', 'up', 0, 30.55),
     (2, 'it', 'clearly', 2, 32.25), (2, 'perplexity', 'do', 2, 36.4), (2, 'learn', 'done', 0, 38.8),
     (2, 'perplexity', 'today', 3, 42.0)]
DUR = 48.5; out = np.zeros(int(DUR * sr)); words = []; prev_end = 0
for take, a, b, occ, at in P:
    src = T[take][0]; s, e, ws = span(W[take], a, b, occ)
    s0, e0 = max(0, s - .06), e + .25
    seg = src[int(s0 * sr):int(e0 * sr)].copy(); f = int(.012 * sr)
    seg[:f] *= np.linspace(0, 1, f); seg[-f * 3:] *= np.linspace(1, 0, f * 3)
    at = max(at, prev_end + .2)            # never overlap: a line waits for the previous one
    i = int((at - .06) * sr); out[i:i + len(seg)] += seg; prev_end = at - .06 + len(seg) / sr
    for w_ in ws: words.append([norm(w_[0]), round(at + w_[1] - s, 2), round(at + w_[2] - s, 2)])
sf.write('vo_placed.wav', out, sr); json.dump(words, open('words_placed.json', 'w'))
print(' '.join(f'{w}@{t}' for w, t, _ in words)); print('ends', round(prev_end, 2))
