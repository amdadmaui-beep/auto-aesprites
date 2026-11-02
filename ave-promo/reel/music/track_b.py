# Draft B — brighter, punchier "tech launch" bed: 112 BPM, A minor → C major lift, 15s.
# Plucky stabs and a clean drop, closer to an Apple/Nothing ad than draft A's warm keys.
src = open('track.py').read(); exec(src[:src.index('# ---- harmony')].replace('BPM = 96', 'BPM = 112'))
def pluck(t0, n, g=.06, pan=0., dec=.16, cut=6000):
    f = nf(n); t = tv(.8)
    x = np.sin(2*np.pi*f*t + 2.2*np.exp(-t/.03)*np.sin(2*np.pi*f*2*t)) * np.exp(-t/dec)
    add(t0, lp(x*np.minimum(1, t/.001), cut), g, pan, .25, .4)
def stabc(t0, notes, g=.06, d=.12, cut=3200):
    t = tv(d + .3); x = np.zeros_like(t)
    for k, n in enumerate(notes): f = nf(n); x += signal.sawtooth(2*np.pi*f*t*(1+.003*(k-1))) + .4*signal.square(2*np.pi*f*.5*t)
    x = lp(x/len(notes), cut) * np.minimum(1, t/.002) * np.exp(-np.maximum(0, t-d)/.05)
    add(t0, x, g, 0, .35, .25)
def clap(t0, g=.14):
    t = tv(.35); x = np.zeros_like(t)
    for d in (0, .008, .016, .026): x += np.roll(bp(noise(.35), 1000, 5000)*np.exp(-t/.01), int(d*SR))
    add(t0, x + .5*bp(noise(.35), 1200, 6000)*np.exp(-t/.11), g, .05, .45)
def glitch(t0, n=6, g=.025):
    for k in range(n):
        t = tv(.02); f = 3000 + 900*((k*7) % 5); add(t0 + k*.028, np.sign(np.sin(2*np.pi*f*t))*np.exp(-t/.004), g*(1-k/n), (-1)**k*.5)
PROG = [(['A3','C4','E4','G4'],'A1'), (['F3','A3','C4','E4'],'F1'), (['C3','E3','G3','B3'],'C2'), (['G3','B3','D4','A4'],'G1')]
LIFT = [(['F3','A3','C4','E4','G4'],'F1'), (['G3','B3','D4','F4'],'G1'), (['A3','C4','E4','B4'],'A1'), (['C4','E4','G4','D5'],'C2')]
HOOK = [(0,'E5'),(.5,'G5'),(.75,'A5'),(1.25,'G5'),(1.5,'E5'),(2.0,'D5'),(2.5,'E5'),(3.0,'C5')]          # in beats, one bar
# bar 1 (0–2.1s): intro — glitch, filtered plucks of the hook, riser into the 99 hit
glitch(0.02, 8)
for k, (b, n) in enumerate(HOOK): pluck(.15 + b*BEAT*.5, n, .045, -.3+.08*k, .14, 2500 + 300*k)
pad(0, BAR, ['A3','E4','G4'], .03, 900)
riser(.9, BAR, .07)
for k in range(8): snare(BAR - 8*S16 + k*S16, .015 + .01*k, .15)
# bars 2–5 (2.1–10.7s): four bars of groove; a different chord, hook variation and bass figure each bar
BASS = [[0,3,6,8,11,14],[0,2,6,8,10,13],[0,3,5,8,11,12,14],[0,4,6,8,10,11,14]]
for bi in range(4):
    b0 = BAR*(1+bi); notes, root = (PROG if bi < 2 else LIFT)[bi*1 % 4] if False else ((PROG+LIFT)[bi*2], (PROG+LIFT)[bi*2][1])
    notes = notes[0] if isinstance(notes, tuple) else notes
    n2, r2 = (PROG+LIFT)[bi*2+1]
    impact(b0, .32 if bi in (0, 2) else .1)
    for half, (nn, rr) in enumerate([(notes, root), (n2, r2)]):
        h0 = b0 + half*BAR/2
        for s in (0, 3, 6): stabc(h0 + s*S16, nn, .05 if bi < 2 else .06)
        for s in BASS[bi]:
            if s < 8: sub(h0 + s*S16, S16*1.7, rr, .25, 4 if s == 0 else 0)
    for s in range(16):
        t = b0 + s*S16 + (.01 if s % 2 else 0)
        if s in (0, 6, 8) or (bi >= 2 and s in (3, 11)): kick(b0 + s*S16, .46 if s == 0 else .36)
        if s in (4, 12): clap(b0 + s*S16, .15)
        hat(t, .024 if s % 4 == 2 else .012, .3, op=(s in (6, 14)))
        if bi >= 2 and s % 2: shaker(t, .016)
    shift = [0, 2, -1, 3][bi]
    for k, (b, n) in enumerate(HOOK):
        idx = SCALE_A.index(n) if False else None
    for k, (b, n) in enumerate(HOOK):
        nn = n if shift == 0 else ['C5','D5','E5','G5','A5','C6','D6'][min(6, max(0, ['C5','D5','E5','G5','A5'].index(n if n in ['C5','D5','E5','G5','A5'] else 'E5') + shift))]
        pluck(b0 + b*BEAT, nn, .055 if bi < 2 else .065, -.35+.1*k, .2, 6500)
    if bi == 1:
        for k in range(4): snare(b0 + BAR - 4*S16 + k*S16, .03+.025*k, .2)
        riser(b0 + BAR - 1.0, b0 + BAR, .07)
    if bi in (0, 2): glitch(b0 + BAR - 2*S16, 5, .02)
# bar 6 (10.7–12.9s): breakdown — drums out, pad + plucked hook, half-time
b0 = BAR*5; impact(b0, .2)
pad(b0, BAR, ['F3','A3','C4','E4','G4'], .05, 1800)
for k, (b, n) in enumerate(HOOK): pluck(b0 + b*BEAT, n, .05, -.3+.08*k, .35, 4000)
sub(b0, BAR*.48, 'F1', .2); sub(b0 + BAR/2, BAR*.48, 'G1', .2)
riser(b0 + BAR - .9, b0 + BAR, .06)
# bar 7 (12.9–15s): final hit + resolve on C major
b0 = BAR*6; impact(b0, .3); kick(b0, .5); clap(b0 + BEAT, .1)
stabc(b0, ['C4','E4','G4','B4','D5'], .07, .5, 4500)
pad(b0, 3.0, ['C3','G3','E4','B4'], .05, 2400)
for k, n in enumerate(['G5','B5','D6','E6']): pluck(b0 + .2 + k*S16*1.5, n, .05, -.3+.2*k, .7, 8000)
sub(b0, 1.2, 'C2', .24, 4)
for s in range(8): hat(b0 + BEAT + s*S16*2, .012, .3)
ir_t = tv(1.4); ir = rng.standard_normal(len(ir_t)) * np.exp(-ir_t/.38); ir /= np.sqrt((ir**2).sum())
for c in (0, 1): L[:, c] += fftconvolve(VERB[:, c], ir*(1 if c else .96), 'full')[:N].astype(np.float32)*.35
d1 = int(BEAT*.75*SR); srcd = lp(DLY.mean(1), 5000)
for k in range(1, 6):
    d = d1*k
    if d < N: L[d:, k % 2] += srcd[:N-d]*(.4**k)
fo = int(.5*SR); L[-fo:] *= np.linspace(1, 0, fo)[:, None]**1.5
L = np.tanh(L*1.2)/1.2
y = np.clip(L, -1, 1); w = wave.open('music_b.wav', 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((y*32767).astype(np.int16).tobytes()); w.close()
print('ok', float(np.abs(L).max()), 'bar', BAR)
