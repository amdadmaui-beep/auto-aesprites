# ------------------------------------------------------------ V3 original score — 120 BPM, D dorian
# Apple-ad clarity × Nothing-style glitch: crisp layered drums, funky 16th bass with slides, FM bell motif with
# ping-pong delay, offbeat stabs. Arc: hook → build → full → groove (stop-time on "watched") → lift → reduction →
# drop → impact on "hit" → resolve → end sting. Every section boundary sits on a picture cue.
from scipy.signal import fftconvolve
BEAT = .5; S16 = BEAT / 4
echo, verb = buf(), buf()
kicks = []
def kick2(t0, g=.5):
    t = tv(.5); f = 46 + 120 * np.exp(-t / .022); x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / .22)
    x = np.tanh(x * 2.0) * .8 + .5 * bp(noise(.5), 2500, 9000) * np.exp(-t / .0025)
    add(music, t0, x, g); kicks.append(t0)
def snare(t0, g=.15, send=.35):
    t = tv(.4); x = np.zeros_like(t)
    for d in (0, .008, .017): x += np.roll(bp(noise(.4), 1000, 5200) * np.exp(-t / .011), int(d * SR))
    x += .55 * bp(noise(.4), 1400, 7000) * np.exp(-t / .07) + .35 * np.sin(2 * np.pi * 190 * t) * np.exp(-t / .03)
    add(music, t0, x, g, -.04); add(verb, t0, x, g * send)
def hat2(t0, g=.025, pan=.25, op=False):
    t = tv(.45); x = hp(noise(.45), 8000) * np.exp(-t / (.14 if op else .022)); add(music, t0, x, g, pan)
def shaker(t0, g=.012, pan=-.35):
    t = tv(.08); x = bp(noise(.08), 5000, 12000) * np.sin(np.pi * np.minimum(1, t / .06)) ** 2; add(music, t0, x, g, pan)
def bell(t0, n, g=.07, pan=0., dec=.5, send=.35, oct=0):
    f = nf(n) * 2 ** oct; t = tv(2.0)
    x = np.sin(2 * np.pi * f * t + 1.6 * np.exp(-t / .12) * np.sin(2 * np.pi * f * 3.5 * t)) * np.exp(-t / dec)
    x += .25 * np.sin(2 * np.pi * f * 2 * t) * np.exp(-t / (dec * .4))
    x *= np.minimum(1, t / .0015); add(music, t0, x, g, pan); add(echo, t0, x, g * send, pan)
def fbass(t0, d, n, g=.16, slide=0., ghost=False):
    f = nf(n); t = tv(d + .05); ff = f * 2 ** (-3 * slide * np.exp(-t / .045) / 12)                    # slide up into the note
    ph = 2 * np.pi * np.cumsum(ff) / SR
    x = np.tanh(2.6 * (np.sin(ph) + .35 * np.sin(2 * ph + .4)))
    cut = 350 + (2200 if not ghost else 700) * np.exp(-t / .06)            # filter envelope = the "funk"
    y = np.zeros_like(x); seg = 256
    for i in range(0, len(x), seg):
        y[i:i + seg] = lp(x[max(0, i - 512):i + seg], cut[i])[-len(x[i:i + seg]):]
    e = np.minimum(1, t / .003) * np.clip((d + .04 - t) / .03, 0, 1)
    add(music, t0, y * e, g * (.45 if ghost else 1))
def stab(t0, notes, g=.05, pan=0., d=.11):
    t = tv(d + .1); x = np.zeros_like(t)
    for k, n in enumerate(notes):
        f = nf(n); x += signal.sawtooth(2 * np.pi * f * t * (1 + .002 * (k - 1))) + .5 * signal.square(2 * np.pi * f * 1.003 * t)
    x = lp(x / len(notes), 2600) * np.minimum(1, t / .002) * np.exp(-np.maximum(0, t - d) / .02) * np.exp(-t / .3)
    add(music, t0, x, g, pan); add(echo, t0, x, g * .18, -pan)
def pad2(t0, t1, notes, g=.04, cut=1400, att=.4, rel=.8):
    d = t1 - t0 + rel; t = tv(d); L = np.zeros_like(t); R = np.zeros_like(t)
    for n in notes:
        f = nf(n); L += signal.sawtooth(2 * np.pi * f * .998 * t + rng.random() * 6); R += signal.sawtooth(2 * np.pi * f * 1.002 * t + rng.random() * 6)
    e = np.minimum(1, t / att) * np.where(t > t1 - t0, np.exp(-(t - (t1 - t0)) / (rel / 3)), 1)
    add(music, t0, np.stack([lp(L, cut), lp(R, cut)], 1) * e[:, None] / len(notes), g)
def subdrop(t0, g=.3, d=1.4, f0=55):
    t = tv(d); f = f0 * (1 + .9 * np.exp(-t / .08)); add(music, t0, np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / (d / 3)), g)
def noiseriser(t0, t1, g=.06):
    d = t1 - t0; t = tv(d); z = noise(d); y = np.zeros_like(t); seg = 512
    for i in range(0, len(t), seg):
        fc = 400 * (20 ** (i / len(t))); y[i:i + seg] = bp(z[max(0, i - 1024):i + seg], fc * .7, fc * 1.5)[-len(z[i:i + seg]):]
    add(music, t0, y * (t / d) ** 2.2, g)
def crash(t0, g=.06):
    t = tv(2.2); x = hp(noise(2.2), 4500) * np.exp(-t / .7) * (1 + .3 * np.sin(2 * np.pi * 7 * t)); add(music, t0, x, g, .1); add(verb, t0, x, g * .3)

CH = [('D2', ['F3', 'A3', 'C4', 'E4']),            # Dm9
      ('G1', ['F3', 'B3', 'E4', 'A4']),            # G13
      ('A#1', ['D3', 'F3', 'A3', 'C4']),           # Bbmaj9 (no 3rd doubling)
      ('A1', ['G3', 'C#4', 'F4', 'A4'])]           # A7(b13)
def chord_at(t): return CH[int(t // 2) % 4]
def up(n, k=1): return n[:-1] + str(int(n[-1]) + k)
MOTIF = [(0, 'A4'), (.375, 'C5'), (.75, 'D5'), (1.0, 'F5'), (1.25, 'E5'), (1.5, 'D5'), (1.625, 'C5')]   # the hook (2s)
ANSWER = [(0, 'D5'), (.25, 'F5'), (.5, 'A5'), (.875, 'G5'), (1.25, 'E5'), (1.5, 'C5')]
# 16-step patterns per 2s bar
K_BUILD = [0, 8]; K_FUNK = [0, 3, 8, 10, 11]; K_LIFT = [0, 3, 6, 8, 10, 14]
BASS_FUNK = [(0, 2, 0, 0), (3, 1, 1, 0), (4, 1, 0, 1), (6, 1, 1, 0), (7, 1, 0, 1), (8, 2, 0, 0), (10, 1, 0, 0), (11, 1, 1, 0), (13, 1, 0, 1), (14, 2, 0, 0)]  # (step, len16, octave, ghost)
def bar_groove(b0, t1, kp, hats=2, snares=True, bassOn=True, stabs=True, motif=None, mg=.06, shk=False, bg=.15, ts=None):
    ts = b0 if ts is None else ts
    root, notes = chord_at(b0)
    for s in range(16):
        t = b0 + s * S16 + (.018 if s % 2 else 0)            # swung 16ths
        if t >= t1: break
        if t < ts: continue
        if s in kp: kick2(b0 + s * S16, .42 if s == 0 else .34)
        if snares and s in (4, 12): snare(b0 + s * S16, .15)
        if snares and s in (7, 15) and rng.random() < .5: snare(t, .03, .1)   # ghost snare
        if hats == 2 or (hats == 1 and s % 2 == 0): hat2(t, (.026 if s % 4 == 2 else .016 if s % 2 else .02), .25)
        if hats and s == 14: hat2(t, .02, .3, op=True)
        if shk and s % 2: shaker(t)
        if stabs and s in (2, 6, 11): stab(t, notes, .05, -.25 if s == 6 else .25)
    if bassOn:
        for s, l, o, gh in BASS_FUNK:
            t = b0 + s * S16 + (.018 if s % 2 else 0)
            if ts <= t < t1: fbass(t, l * S16 * .9, up(root, o), bg, slide=(1 if s == 0 else 0), ghost=bool(gh))
    if motif:
        for i, (dt, n) in enumerate(motif):
            if ts <= b0 + dt < t1: bell(b0 + dt, n, mg, -.3 + .1 * i)
def stutter(t0, slice_=S16 / 2, reps=4):   # Nothing-style glitch: retrigger a slice of the music bus
    i = int(t0 * SR); n = int(slice_ * SR); seg = music[i:i + n].copy()
    for k in range(reps):
        a = i + k * n; music[a:a + n] = seg * (1 - .12 * k)

def score_v3():
    # 1 · hook 0–4: bell motif, sub kick on the one, ticks; space for the voice
    for b0 in (0.0, 2.0):
        for i, (dt, n) in enumerate(MOTIF): bell(b0 + dt, n, .075, -.3 + .1 * i)
        kick2(b0, .3); hat2(b0 + 1.0, .015, .3)
        for s in (2, 6, 10, 14): tickp(b0 + s * S16, .02, 6200, .4)
    pad2(0.0, 4.0, ['D3', 'A3', 'E4'], .025, 900)
    fbass(2.0, .9, 'D2', .1, 1); fbass(3.0, .25, 'D2', .08)
    stab(C['itHit'], CH[0][1], .06)
    for k, s in enumerate(np.arange(3.5, 4.0, S16 / 2)): snare(s, .02 + .012 * k, .1)      # roll into the build
    # 2 · build 4–8 (cards): kick 1 & 3, claps on 2 & 4, bass enters, answer phrase
    for b0 in (4.0, 6.0):
        bar_groove(b0, 8.0, K_BUILD, hats=1, stabs=False, motif=ANSWER if b0 == 6.0 else MOTIF, mg=.05, bg=.12)
    noiseriser(6.9, 7.45, .05); crash(7.45, .05)
    # 3–4 · full 8–16 (dashboard): funk kick, swung 16ths, stabs, motif up an octave every other bar
    for k, b0 in enumerate(np.arange(8.0, 16.0, 2.0)):
        bar_groove(b0, 16.6, K_FUNK, hats=2, motif=[(dt, up(n)) for dt, n in MOTIF] if k % 2 else None, mg=.04, shk=True)
    for s in (9.75, 11.75, 13.75, 15.75): stutter(s)
    noiseriser(16.0, 16.6, .05); crash(16.6, .06)
    # 5 · groove 16–19.5 (feed): leaner for narration
    for b0 in (16.0, 18.0):
        bar_groove(b0, min(b0 + 2, C['reduce']), K_FUNK, hats=1, stabs=b0 == 18.0, bg=.12)
    # stop-time: silence 19.5 → accent on "watched" → groove resumes on the next beat
    kick2(C['watched'], .45); stab(C['watched'], ['D3', 'F3', 'A3', 'C4', 'E4'], .08, 0, .25); crash(C['watched'], .07); subdrop(C['watched'], .18, 1.0)
    bar_groove(20.0, 20.8, K_FUNK, hats=2, stabs=True, bg=.13)
    # 6 · lift 20.8–25.3 (range): fullest; motif and answer trade, fills at every bar end
    for k, b0 in enumerate((20.0, 22.0, 24.0)):
        bar_groove(b0, 25.3, K_LIFT, hats=2, motif=(MOTIF if k % 2 else [(dt, up(n)) for dt, n in ANSWER]), mg=.05, shk=True, bg=.15, ts=20.8 if k == 0 else None)
    crash(20.8, .06)
    for b in (22.75, 23.75, 24.75):                                   # fills
        for k in range(4): snare(b + k * S16, .04 + .025 * k, .2)
    for s in (21.75, 23.25): stutter(s, S16 / 4, 6)
    noiseriser(24.6, 25.3, .07)
    # 7 · reduction 25.3–27.45: pad + heartbeat bass, bell fragments
    pad2(25.3, 27.6, ['D3', 'A3', 'C4', 'E4', 'F4'], .05, 900, .25, .5); crash(25.3, .05)
    for t in np.arange(25.3, 27.4, 1.0): kick2(t, .2); fbass(t, .3, 'D2', .09)
    for dt, n in [(.5, 'A4'), (.875, 'C5'), (1.25, 'D5')]: bell(25.75 + dt + .25, n, .035, -.2, .7, .5)
    # drop 27.45 → 28.75: near silence, reverse swell + riser into the impact
    noiseriser(27.6, C['hit'], .08)
    t = tv(C['hit'] - 27.6); sw = lp(noise(len(t) / SR), 1200) * (t / t[-1]) ** 4; add(music, 27.6, sw, .12)
    # impact on "hit": sub drop, kick, crash, chord, then the groove resolves (grid restarts on the hit)
    H = C['hit']; kick2(H, .55); subdrop(H, .32, 1.6, 41.2); crash(H, .09); stab(H, CH[0][1] + ['D5'], .08, 0, .35)
    for k, b0 in enumerate((H, H + 2.0)):
        bar_groove(b0, C['sting'], K_FUNK if k == 0 else K_BUILD, hats=2 if k == 0 else 1, stabs=k == 0,
                   motif=MOTIF if k == 0 else None, mg=.05, bg=.13)
    # end sting: bell chord + sub + glitch tail, rings to the end
    Sg = C['sting']; kick2(Sg, .45); subdrop(Sg, .22, 1.2)
    for i, n in enumerate(['D5', 'F5', 'A5', 'E6']): bell(Sg + i * .03, n, .06, -.3 + .2 * i, 1.0, .5)
    stab(Sg, ['D3', 'A3', 'C4', 'E4'], .06, 0, .4); crash(Sg, .06)
    for k in range(6): tickp(Sg + .3 + k * .045, .02 * (1 - k / 6), 5000 + 700 * k, .5 - .2 * k)
    # sidechain pump from the kick list on music (not on the bells' tails), then sends
    pump = np.ones(N, np.float32)
    for kt in kicks:
        i = int(kt * SR); n = int(.22 * SR); j = min(N, i + n)
        if j > i: pump[i:j] = np.minimum(pump[i:j], .55 + .45 * (np.arange(j - i) / n) ** .7)
    music[:] *= pump[:, None]
    # ping-pong delay (3/16 L, 3/8 R) and a small room on snares/crash
    E = np.zeros_like(echo); d1, d2 = int(3 * S16 * SR), int(6 * S16 * SR)
    src_ = lp(echo.mean(1), 5000)
    for k in range(1, 6):
        d = d1 * k; side = 0 if k % 2 else 1
        if d < N: E[d:, side] += src_[:N - d] * (.42 ** k)
    music[:] += E
    ir_t = tv(.9); ir = rng.standard_normal(len(ir_t)) * np.exp(-ir_t / .22); ir /= np.sqrt((ir ** 2).sum())
    for c in (0, 1):
        music[:, c] += fftconvolve(verb[:, c], ir * (1 if c else .97), 'full')[:N].astype(np.float32) * .5
    # stop-time gate: the band cuts out between "reduce" and "watched" (only a breath of riser remains)
    i, j = int((C['reduce'] + .03) * SR), int((C['watched'] - .004) * SR); f = int(.012 * SR)
    gte = np.ones(N, np.float32); gte[i:j] = .05; gte[i:i + f] = np.linspace(1, .05, f); gte[j - f:j] = np.linspace(.05, 1, f)
    music[:] *= gte[:, None]
    noiseriser(C['reduce'] + .03, C['watched'], .045)
