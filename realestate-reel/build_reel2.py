# Real estate "Before / After" reel V2 (4K): same cut points and audio as the client's reference, Mixkit footage,
# + diagonal shard and vertical panel transitions (from the reference), a designed ambient backdrop, AVE Studio outro.
# usage: python build_reel2.py <clips_dir> <reference_audio.wav> <sfx_library_dir> <out.mp4>
import sys, os, subprocess, numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
CLIPS, AUDIO, SFXLIB, OUT = sys.argv[1:5]
HERE = os.path.dirname(os.path.abspath(__file__))
S = 2; W, H, FPS = 1080 * S, 1920 * S, 30                     # 2160×3840
BX, BY, BW, BH = 105 * S, 399 * S, 857 * S, 482 * S           # Before card
AX, AY, AW, AH = 28 * S, 1032 * S, 1012 * S, 569 * S          # After card
RAD = 24 * S
FONT = f'{HERE}/InterDisplay-SemiBold.otf'

def dur(c): return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f'{CLIPS}/{c}.mp4'], capture_output=True, text=True).stdout)
def decode(c, t0, n, w, h, speed=1., crop=None):
    span = n / FPS * speed + .2; vf = []
    if crop: x, y, cw, ch = crop; vf.append(f'crop=iw*{cw}:ih*{ch}:iw*{x}:ih*{y}')
    vf += [f'setpts=PTS/{speed}', f'fps={FPS}', f'scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos', f'crop={w}:{h}', 'unsharp=5:5:0.45']
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(t0), '-t', str(span), '-i', f'{CLIPS}/{c}.mp4', '-vf', ','.join(vf), '-frames:v', str(n),
                          '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
    a = np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3)
    if len(a) < n: a = np.concatenate([a, np.repeat(a[-1:], n - len(a), 0)])
    return a[:n]                                              # uint8: 4K frames stay affordable in memory
F = lambda a: a.astype(np.float32) / 255

# ---------------------------------------------------------------- looks
def lum(x): return (x * np.array([.2126, .7152, .0722], np.float32)).sum(-1, keepdims=True)
def before_look(x):
    l = lum(x); x = l + (x - l) * .72; x = .05 + x * .80; x = x * np.array([.97, 1, 1.03], np.float32); return np.clip(x, 0, 1)
yy, xx = np.mgrid[0:AH, 0:AW].astype(np.float32)
VIG = (1 - .10 * (((xx - AW / 2) / (AW / 2)) ** 2 + ((yy - AH / 2) / (AH / 2)) ** 2) ** 1.2).astype(np.float32)[..., None]
WARM = np.array([1.035, 1, .955], np.float32)
def after_look(x):
    x = 1 - (1 - np.clip(x, 0, 1)) ** 1.35; l = lum(x); x = l + (x - l) * 1.16
    c = np.clip(x, 0, 1); x = x + .07 * np.sin(np.pi * c) * (c - .5) * 2
    return np.clip(x * WARM * VIG, 0, 1)
def relight(x, k): return x * np.array([.8, .9, 1.25], np.float32) * .32 * (1 - k) + x * k
def ease(u): u = min(1, max(0, u)); return 1 - (1 - u) ** 3

# ---------------------------------------------------------------- shapes
def rrect_mask(w, h, r, ss=2):
    m = Image.new('L', (w * ss, h * ss), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, w * ss - 1, h * ss - 1), r * ss, fill=255)
    return np.asarray(m.resize((w, h), Image.LANCZOS), np.float32)[..., None] / 255
def shadow_alpha(w, h, r, blur=26 * S, dy=14 * S, op=.30):
    pad = blur * 3; m = Image.new('L', (w + 2 * pad, h + 2 * pad), 0); ImageDraw.Draw(m).rounded_rectangle((pad, pad + dy, pad + w, pad + h + dy), r, fill=int(255 * op))
    return np.asarray(m.filter(ImageFilter.GaussianBlur(blur)), np.float32)[..., None] / 255, pad
MB, MA = rrect_mask(BW, BH, RAD), rrect_mask(AW, AH, RAD)
def paste(canvas, img, x, y, mask):
    h, w = img.shape[:2]; reg = canvas[y:y + h, x:x + w]; reg[:] = reg * (1 - mask) + img * mask

# ---------------------------------------------------------------- page design: ambient backdrop + grid + chips + header
SHADOWS = np.ones((H, W, 1), np.float32)
for (x, y, w, h) in ((BX, BY, BW, BH), (AX, AY, AW, AH)):
    s, pad = shadow_alpha(w, h, RAD); y0, x0 = y - pad, x - pad
    ys, xs, ye, xe = max(0, y0), max(0, x0), min(H, y0 + s.shape[0]), min(W, x0 + s.shape[1])
    SHADOWS[ys:ye, xs:xe] *= 1 - s[ys - y0:ye - y0, xs - x0:xe - x0]
CREAM = np.array([.965, .953, .933], np.float32)
def ambient(after_u8):
    """the current After shot, cover-fitted to the page, hugely blurred and washed toward cream"""
    im = Image.fromarray(after_u8).resize((96, 54), Image.BILINEAR)
    sq = im.crop((96 / 2 - 54 * 9 / 32, 0, 96 / 2 + 54 * 9 / 32, 54)).resize((54, 96), Image.BILINEAR).filter(ImageFilter.GaussianBlur(5))
    a = np.asarray(sq.resize((W // 8, H // 8), Image.BILINEAR).resize((W, H), Image.BILINEAR), np.float32) / 255
    return a * .38 + CREAM * .62
# overlay layer (grid, corner ticks, chips, header) drawn once, alpha-composited each frame
ov = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
g = 60 * S
for x in range(0, W, g): d.line([(x, 0), (x, H)], fill=(20, 18, 12, 14), width=S)
for y in range(0, H, g): d.line([(0, y), (W, y)], fill=(20, 18, 12, 14), width=S)
for (x, y, w, h) in ((BX, BY, BW, BH), (AX, AY, AW, AH)):          # architectural corner ticks around each card
    m, L = 18 * S, 34 * S
    for cx, cy, sx, sy in ((x - m, y - m, 1, 1), (x + w + m, y - m, -1, 1), (x - m, y + h + m, 1, -1), (x + w + m, y + h + m, -1, -1)):
        d.line([(cx, cy), (cx + sx * L, cy)], fill=(20, 18, 12, 120), width=2 * S); d.line([(cx, cy), (cx, cy + sy * L)], fill=(20, 18, 12, 120), width=2 * S)
fchip = ImageFont.truetype(FONT, 40 * S)
def chip(text, cx, cy, dark):
    tw = d.textlength(text, font=fchip); pw, ph = tw + 56 * S, 72 * S; x0, y0 = cx - pw / 2, cy - ph / 2
    sh = Image.new('RGBA', (W, H), (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle((x0, y0 + 6 * S, x0 + pw, y0 + ph + 6 * S), ph / 2, fill=(0, 0, 0, 70))
    ov.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10 * S)))
    d.rounded_rectangle((x0, y0, x0 + pw, y0 + ph), ph / 2, fill=(14, 13, 10, 255) if dark else (255, 255, 255, 255))
    d.text((cx - tw / 2, cy - 27 * S), text, font=fchip, fill=(255, 255, 255, 255) if dark else (14, 13, 10, 255))
chip('Before', W / 2, BY - 62 * S, False); chip('After', W / 2, AY - 62 * S, True)
logo = Image.open(f'{HERE}/ave_logo.png').convert('RGBA'); lw = 150 * S; lg = logo.resize((lw, int(lw * logo.height / logo.width)), Image.LANCZOS)
ov.alpha_composite(lg, (int(W / 2 - lw / 2), 132 * S))
fsmall = ImageFont.truetype(FONT, 22 * S); tag = 'S T U D I O   ·   R E A L   E S T A T E   E D I T S'
d.text((W / 2 - d.textlength(tag, font=fsmall) / 2, 132 * S + lg.height + 22 * S), tag, font=fsmall, fill=(20, 18, 12, 170))
OV = np.asarray(ov, np.float32) / 255; OVA, OVC = OV[..., 3:4], OV[..., :3]

# ---------------------------------------------------------------- transitions (from the reference)
def shard_wipe(a, b, u, n=5, slant=.42):
    """diagonal glass shards of the next shot land one after another, left to right"""
    out = a.copy(); xs = xx - slant * (yy - AH / 2); band = (AW + slant * AH) / n; idx = np.floor((xs + slant * AH / 2) / band)
    for i in range(n):
        p = ease((u - i * .13) / .38)
        if p <= 0: continue
        off = int((1 - p) * 70 * S); sh = int((1 - p) * (-1) ** i * 40 * S)   # each shard slides up into place and its content settles
        m = (idx == i)
        if off or sh: m = np.roll(m, -off, 0); src = np.roll(np.roll(b, -off, 0), sh, 1)
        else: src = b
        mm = m[..., None].astype(np.float32); out = out * (1 - mm) + src * mm
        if p < 1:   # a bright glass edge on the shard's leading border
            e = (np.abs(xs - (i * band - slant * AH / 2)) < 2.5 * S) & m; out[e] = out[e] * .4 + .6
    return out if u < 1 else b
def panel_build(a, b, u, n=4, gap=6 * S):
    """vertical panels of the next shot drop in one by one, each with its own offset, then lock together"""
    out = a.copy(); pw = AW / n
    for i in range(n):
        p = ease((u - i * .18) / .34)
        if p <= 0: continue
        x0, x1 = int(i * pw + (gap if p < 1 and i else 0)), int((i + 1) * pw - (gap if p < 1 and i < n - 1 else 0))
        dy = int((1 - p) * (1 if i % 2 else -1) * 90 * S); cy = int((1 - p) * (-1 if i % 2 else 1) * 50 * S)
        col = np.roll(b[:, x0:x1], cy, 0); ys, ye = max(0, dy), min(AH, AH + dy)
        out[ys:ye, x0:x1] = col[ys - dy:ye - dy]
    return out if u < 1 else b

# ---------------------------------------------------------------- the edit (cut points = the reference's pair swaps)
SEG = [
  (0.00, 1.07, '4047', 4.6, 2.0, {'flash': 1}),
  (1.07, 1.63, '3111', 2.0, 1.0, {'relight': 1.40}),
  (1.63, 2.87, '3109', 1.0, 1.0, {}),
  (2.87, 5.23, '4205', 2.0, 7.0, {'trans': ('shard', 4.53, '8603', 22.0 - .70 * 1.5, 1.5)}),     # dusk → shards → manor aerial
  (5.23, 5.80, '8603', 22.0, 1.5, {}),
  (5.80, 6.57, '47286', 3.0, 1.0, {}),
  (6.57, 7.23, '3110', 2.0, 1.0, {}),
  (7.23, 7.97, '43033', 2.0, 1.0, {}),
  (7.97, 8.70, '4488', 3.0, 1.0, {}),
  (8.70, 10.13, '4029', 12.0, 6.0, {'trans': ('panel', 9.55, '4046', 1.0 - .58, 1.0)}),          # terrace → panels → white suite
  (10.13, 10.83, '4046', 1.0, 1.0, {}),
  (10.83, 11.57, '6773', 2.0, 1.0, {}),
  (11.57, 13.20, '9902', 5.0, 1.5, {'trans': ('panel', 12.55, '4045', 1.0, 1.0)}),             # aerial → panels → pool (as in the reference)
  (13.20, 14.47, '4045', 1.65, 1.0, {}),
  (14.47, 16.80, '9902', 30.0, 1.5, {'inserts': [(15.90, '40109', 3.0, None), (16.10, '4047', 3.0, (.42, .52, .32, .32)),
                                                   (16.30, '43033', 4.0, (.08, .50, .36, .36)), (16.50, '4045', 3.0, (.05, .55, .40, .40))]}),
  (16.80, 17.37, '3090', 2.0, 1.0, {}),
  (17.37, 18.07, '4196', 3.0, 1.5, {}),
  (18.07, 18.80, '4641', 3.0, 1.0, {}),
  (18.80, 19.57, '3112', 2.0, 1.0, {}),
  (19.57, 20.23, '4047', 9.0, 1.0, {}),
  (20.23, 21.70, '4029', 26.0, 3.0, {'trans': ('box', 21.20, '6773', 8.5, 1.0)}),             # box reveal into the pool garden
  (21.70, 22.37, '6773', 9.0, 1.0, {}),
  (22.37, 23.17, '4488', 14.0, 1.0, {}),
  (23.17, 24.77, '3110', 7.0, 1.0, {'trans': ('iris', 24.57, '43033', 6.0, 1.0)}),
  (24.77, 26.07, '43033', 6.2, 1.0, {'trans': ('shard', 25.40, '47286', 8.0 - .67 * .8, .8)}),  # kitchen → shards → villa
  (26.07, 28.90, '47286', 8.0, .8, {'inserts': [(27.43, '4045', 2.0, (.30, .08, .26, .30)), (27.63, '3110', 3.0, (.44, .44, .26, .30)),
                                                  (27.97, '4047', 2.0, (.52, .22, .34, .38)), (28.40, '43033', 5.0, (.04, .44, .36, .40))]}),
]
IW, IH = int(AW * .84) // 2 * 2, int(AH * .84) // 2 * 2; IX, IY = AX + (AW - IW) // 2 + 18 * S, AY + (AH - IH) // 2; MI = rrect_mask(IW, IH, RAD)
OUTRO = 2.2
enc = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                        '-c:v', 'libx264', '-preset', 'medium', '-crf', '16', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', OUT + '.video.mp4'], stdin=subprocess.PIPE)
def emit(fr): enc.stdin.write((np.clip(fr, 0, 1) * 255).astype(np.uint8).tobytes())
def compose(still, after_f, t):
    amb = ambient((after_f * 255).astype(np.uint8)); fr = amb * SHADOWS
    fr = fr * (1 - OVA) + OVC * OVA
    paste(fr, still, BX, BY, MB); paste(fr, after_f, AX, AY, MA); return fr
last = None
for t0, t1, c, sa, sp, fx in SEG:
    f0, f1 = int(round(t0 * FPS)), int(round(t1 * FPS)); n = f1 - f0
    assert sa + n / FPS * sp <= dur(c) + .05, (c, sa, sp, n)
    still = before_look(F(decode(c, sa, 1, BW, BH)[0]))
    vid = decode(c, sa, n, AW, AH, sp)
    tr = None
    if 'trans' in fx:
        kind, tt, ct, st, spt = fx['trans']; nt = f1 - int(round(tt * FPS)); tr = (kind, tt, decode(ct, st, nt, AW, AH, spt), (t1 - tt))
    ins = [(ti, decode(ci, si, 12, IW, IH, 1., cr)) for ti, ci, si, cr in fx.get('inserts', [])]
    for k in range(n):
        t = (f0 + k) / FPS; a = F(vid[k])
        if 'relight' in fx: a = relight(a, np.clip((t - fx['relight']) / .22, 0, 1))
        if tr:
            kind, tt, tv, td = tr; kt = int(round((t - tt) * FPS))
            if kt >= 0:
                b = F(tv[min(kt, len(tv) - 1)]); u = kt / max(1, td * FPS - 1)
                if kind == 'shard': a = shard_wipe(a, b, u)
                elif kind == 'panel': a = panel_build(a, b, u)
                elif kind == 'box':
                    v = ease(kt / (.38 * FPS)); w, h = int(AW * (.32 + .68 * v)), int(AH * (.32 + .68 * v)); x0, y0 = (AW - w) // 2, (AH - h) // 2
                    m = rrect_mask(w, h, int(RAD * (1 - v) + 4)); a[y0:y0 + h, x0:x0 + w] = a[y0:y0 + h, x0:x0 + w] * (1 - m) + b[y0:y0 + h, x0:x0 + w] * m
                elif kind == 'iris':
                    v = min(1, kt / (.2 * FPS)) ** 2; R = 30 * S + v * 1250 * S
                    m = np.clip(R - np.sqrt((xx - AW * .6) ** 2 + (yy - AH * .5) ** 2) + .5, 0, 1)[..., None]; a = a * (1 - m) + b * m
        a = after_look(a)
        if fx.get('flash'): a = a + (1 - a) * max(0, 1 - t / .12)
        fr = compose(still, a, t)
        for j, (ti, iv) in enumerate(ins):
            tn = ins[j + 1][0] if j + 1 < len(ins) else t1
            if ti <= t < tn:
                ki = min(len(iv) - 1, int((t - ti) * FPS)); s = .9 + .1 * ease((t - ti) / .1); img = F(iv[ki])
                if s < .999:
                    im = Image.fromarray(iv[ki]).resize((int(IW * s), int(IH * s)), Image.LANCZOS); img = np.asarray(im, np.float32) / 255
                    paste(fr, img, IX + (IW - img.shape[1]) // 2, IY + (IH - img.shape[0]) // 2, rrect_mask(img.shape[1], img.shape[0], RAD))
                else: paste(fr, img, IX, IY, MI)
        emit(fr); last = (still, a)
    print(f'{t0:5.2f}-{t1:5.2f} {c}', flush=True)

# ---------------------------------------------------------------- outro: the AVE logo builds itself from the same vertical panels
amb = ambient((last[1] * 255).astype(np.uint8)); base = amb * .35 + CREAM * .65
gx, gy = np.mgrid[0:H, 0:W]; base = base * (1 - OVA * .6) + OVC * OVA * .6   # keep the grid, softly
LW = 1300 * S // 2 * 2 // 2; lg2 = logo.resize((LW, int(LW * logo.height / logo.width)), Image.LANCZOS); LA = np.asarray(lg2, np.float32) / 255
lx, ly = (W - LW) // 2, int(H * .44) - lg2.height // 2
fst = ImageFont.truetype(FONT, 46 * S); st = 'S T U D I O'
stl = Image.new('RGBA', (W, 120 * S), (0, 0, 0, 0)); ImageDraw.Draw(stl).text(((W - ImageDraw.Draw(stl).textlength(st, font=fst)) / 2, 10 * S), st, font=fst, fill=(14, 13, 10, 255))
STA = np.asarray(stl, np.float32) / 255; sty = ly + lg2.height + 70 * S
fur = ImageFont.truetype(FONT, 30 * S); ur = 'Real estate photo → cinematic video'
url = Image.new('RGBA', (W, 80 * S), (0, 0, 0, 0)); ImageDraw.Draw(url).text(((W - ImageDraw.Draw(url).textlength(ur, font=fur)) / 2, 10 * S), ur, font=fur, fill=(60, 56, 48, 255))
URA = np.asarray(url, np.float32) / 255; ury = sty + 150 * S
n_out = int(OUTRO * FPS); TP = [0.05 + .12 * i for i in range(4)]
for k in range(n_out):
    t = k / FPS; fr = base.copy()
    # transition in: the last frame's cards fade out quickly
    if t < .2:
        prev = compose(last[0], last[1], 0); fr = prev * (1 - t / .2) + fr * (t / .2)
    pw = LW / 4
    for i in range(4):
        p = ease((t - TP[i]) / .26)
        if p <= 0: continue
        x0, x1 = int(i * pw), int((i + 1) * pw); dy = int((1 - p) * (1 if i % 2 else -1) * 140 * S)
        part = LA[:, x0:x1]; ys = ly + dy; reg = fr[ys:ys + part.shape[0], lx + x0:lx + x1]
        al = part[..., 3:4] * min(1, p * 1.6); reg[:] = reg * (1 - al) + part[..., :3] * al
    so = ease((t - .75) / .35); reg = fr[sty:sty + STA.shape[0]]; al = STA[..., 3:4] * so; reg[:] = reg * (1 - al) + STA[..., :3] * al
    uo = ease((t - 1.0) / .35) * .9; reg = fr[ury:ury + URA.shape[0]]; al = URA[..., 3:4] * uo; reg[:] = reg * (1 - al) + URA[..., :3] * al
    emit(fr)
enc.stdin.close(); enc.wait()

# ---------------------------------------------------------------- audio: the reference track, then the logo's own sound
import wave
def wav(p):
    out = subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-ac', '2', '-ar', '48000', '-f', 'f32le', '-'], capture_output=True).stdout
    return np.frombuffer(out, np.float32).reshape(-1, 2)
SR = 48000; mus = wav(AUDIO); end = SEG[-1][1]; N = int((end + OUTRO) * SR)
mix = np.zeros((N, 2), np.float32); m = mus[:int(end * SR)].copy(); fo = int(.06 * SR); m[-fo:] *= np.linspace(1, 0, fo)[:, None]; mix[:len(m)] += m
bl = sorted(f for f in os.listdir(f'{SFXLIB}/satisfying') if f.startswith('bloop_') and f[6:8].isdigit())
for i, tp in enumerate(TP):   # one bloop per logo panel, then the ding on STUDIO
    x = wav(f'{SFXLIB}/satisfying/{bl[(i * 5 + 3) % len(bl)]}'); s = int((end + tp + .1) * SR); mix[s:s + len(x)] += x[:N - s] * .55
x = wav(f'{SFXLIB}/satisfying/ding_confirm.wav'); s = int((end + .75) * SR); mix[s:s + len(x)] += x[:N - s] * .5
pk = np.abs(mix).max(); mix *= min(1, .97 / pk)
w = wave.open(OUT + '.wav', 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(mix, -1, 1) * 32767).astype(np.int16).tobytes()); w.close()
subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', OUT + '.video.mp4', '-i', OUT + '.wav', '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '320k', '-shortest', '-movflags', '+faststart', OUT])
os.remove(OUT + '.video.mp4'); os.remove(OUT + '.wav'); print('wrote', OUT)
