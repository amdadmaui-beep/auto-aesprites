# Real estate "Before / After" reel: same format, cut points and audio as the client's reference,
# rebuilt with free Mixkit stock footage (Mixkit License: free for commercial use, no attribution).
# "Before" = a still photo of the space (a frame of the clip, flat camera-original look);
# "After"  = the same space as a graded, moving video edit (relights, timelapse, box/iris reveals, detail inserts).
# usage: python build_reel.py <clips_dir> <reference_audio.wav> <out.mp4>
import sys, os, subprocess, numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
CLIPS, AUDIO, OUT = sys.argv[1:4]
HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1080, 1920, 30
# layout = the reference's 720×1280 layout × 1.5
BX, BY, BW, BH = 105, 399, 857, 482          # Before card
AX, AY, AW, AH = 28, 1032, 1011, 569          # After card
RAD = 24
LBL_B_Y, LBL_A_Y = 322, 952                   # label tops

def dur(c): return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f'{CLIPS}/{c}.mp4'], capture_output=True, text=True).stdout)
def decode(c, t0, n, w, h, speed=1., crop=None):
    """n frames of clip c starting at t0 (s), played at `speed`, cover-scaled (optionally from a normalised crop) to w×h."""
    span = n / FPS * speed + .2; vf = []
    if crop: x, y, cw, ch = crop; vf.append(f'crop=iw*{cw}:ih*{ch}:iw*{x}:ih*{y}')
    vf += [f'setpts=PTS/{speed}', f'fps={FPS}', f'scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos', f'crop={w}:{h}']
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(t0), '-t', str(span), '-i', f'{CLIPS}/{c}.mp4', '-vf', ','.join(vf), '-frames:v', str(n),
                          '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
    a = np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3).astype(np.float32) / 255
    if len(a) < n: a = np.concatenate([a, np.repeat(a[-1:], n - len(a), 0)])
    return a[:n]

# ---------------------------------------------------------------- looks
def lum(x): return (x * [.2126, .7152, .0722]).sum(-1, keepdims=True)
def before_look(x):   # the flat, camera-original "photo": duller, a touch dark and cool, no contrast
    l = lum(x); x = l + (x - l) * .72; x = .05 + x * .80; x = x * [.97, 1, 1.03]; return np.clip(x, 0, 1)
def after_look(x, warm=1.):   # the edit: contrast S-curve, richer colour, warm highlights, gentle vignette
    x = 1 - (1 - np.clip(x, 0, 1)) ** 1.35                      # brighter: lift exposure, protect highlights
    l = lum(x); x = l + (x - l) * 1.16
    x = x + .07 * np.sin(np.pi * np.clip(x, 0, 1)) * (np.clip(x, 0, 1) - .5) * 2
    x = x * [1 + .035 * warm, 1, 1 - .045 * warm]
    return np.clip(x * VIG[..., None], 0, 1)
def relight(x, k):    # lights-off (dark, cold) → lights-on (warm), k: 0..1
    dark = np.clip(x * .32 * [.8, .9, 1.25], 0, 1); return dark * (1 - k) + x * k
yy, xx = np.mgrid[0:AH, 0:AW]; VIG = (1 - .10 * (((xx - AW / 2) / (AW / 2)) ** 2 + ((yy - AH / 2) / (AH / 2)) ** 2) ** 1.2).astype(np.float32)

# ---------------------------------------------------------------- shapes
def rrect_mask(w, h, r, ss=3):
    m = Image.new('L', (w * ss, h * ss), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, w * ss - 1, h * ss - 1), r * ss, fill=255)
    return np.asarray(m.resize((w, h), Image.LANCZOS), np.float32)[..., None] / 255
def shadow(w, h, r, blur=26, dy=14, op=.28):
    pad = blur * 3; m = Image.new('L', (w + 2 * pad, h + 2 * pad), 0); ImageDraw.Draw(m).rounded_rectangle((pad, pad + dy, pad + w, pad + h + dy), r, fill=int(255 * op))
    return np.asarray(m.filter(ImageFilter.GaussianBlur(blur)), np.float32)[..., None] / 255, pad
MB, MA = rrect_mask(BW, BH, RAD), rrect_mask(AW, AH, RAD)
def paste(canvas, img, x, y, mask):
    h, w = img.shape[:2]; reg = canvas[y:y + h, x:x + w]; reg[:] = reg * (1 - mask) + img * mask
def paste_shadow(canvas, x, y, w, h):
    s, pad = shadow(w, h, RAD); y0, x0 = y - pad, x - pad
    ys, xs = max(0, y0), max(0, x0); ye, xe = min(H, y0 + s.shape[0]), min(W, x0 + s.shape[1])
    canvas[ys:ye, xs:xe] *= 1 - s[ys - y0:ye - y0, xs - x0:xe - x0]

# ---------------------------------------------------------------- static page: white, labels, shadows
font_b = ImageFont.truetype(f'{HERE}/InterDisplay-SemiBold.otf', 60); font_a = ImageFont.truetype(f'{HERE}/InterDisplay-SemiBold.otf', 66)
page = Image.new('RGB', (W, H), 'white'); d = ImageDraw.Draw(page)
for txt, f, y in (('Before', font_b, LBL_B_Y), ('After', font_a, LBL_A_Y)):
    tw = d.textlength(txt, font=f); d.text(((W - tw) / 2, y), txt, font=f, fill=(0, 0, 0), stroke_width=1, stroke_fill=(0, 0, 0))
BASE = np.asarray(page, np.float32) / 255
paste_shadow(BASE, BX, BY, BW, BH); paste_shadow(BASE, AX, AY, AW, AH)

# ---------------------------------------------------------------- the edit (cut points = the reference's pair swaps)
# (t0, t1, clip, start s, speed, fx)
SEG = [
  (0.00, 1.07, '4047', 4.6, 2.0, {'flash': 1}),                 # sunlight floods the suite
  (1.07, 1.63, '3111', 2.0, 1.0, {'relight': 1.40}),            # lights come on
  (1.63, 2.87, '3109', 1.0, 1.0, {}),
  (2.87, 5.23, '4205', 2.0, 7.0, {}),                           # real timelapse: sunset → dusk
  (5.23, 5.80, '8603', 22.0, 1.5, {}),
  (5.80, 6.57, '47286', 3.0, 1.0, {}),
  (6.57, 7.23, '3110', 2.0, 1.0, {}),
  (7.23, 7.97, '43033', 2.0, 1.0, {}),
  (7.97, 8.70, '4488', 3.0, 1.0, {}),
  (8.70, 10.13, '4029', 12.0, 6.0, {}),                         # pan from the bed out to the terrace
  (10.13, 10.83, '4046', 1.0, 1.0, {}),
  (10.83, 11.57, '6773', 2.0, 1.0, {}),
  (11.57, 13.20, '9902', 5.0, 1.5, {'box': (12.63, '4045', 1.0)}),   # aerial → box reveal of the pool
  (13.20, 14.47, '4045', 1.57, 1.0, {}),
  (14.47, 16.80, '9902', 30.0, 1.5, {'inserts': [(15.90, '40109', 3.0, None), (16.10, '4047', 3.0, (.42, .52, .32, .32)),
                                                   (16.30, '43033', 4.0, (.08, .50, .36, .36)), (16.50, '4045', 3.0, (.05, .55, .40, .40))]}),
  (16.80, 17.37, '3090', 2.0, 1.0, {}),
  (17.37, 18.07, '4196', 3.0, 1.5, {}),
  (18.07, 18.80, '4641', 3.0, 1.0, {}),
  (18.80, 19.57, '3112', 2.0, 1.0, {}),
  (19.57, 20.23, '4047', 9.0, 1.0, {}),
  (20.23, 21.70, '4029', 26.0, 3.0, {}),
  (21.70, 22.37, '6773', 9.0, 1.0, {}),
  (22.37, 23.17, '4488', 14.0, 1.0, {}),
  (23.17, 24.77, '3110', 7.0, 1.0, {'iris': (24.57, '43033', 6.0)}),   # circle reveal into the kitchen
  (24.77, 26.07, '43033', 6.2, 1.0, {}),
  (26.07, 28.90, '47286', 8.0, .8, {'inserts': [(27.43, '4045', 2.0, (.30, .08, .26, .30)), (27.63, '3110', 3.0, (.44, .44, .26, .30)),
                                                  (27.97, '4047', 2.0, (.52, .22, .34, .38)), (28.40, '43033', 5.0, (.04, .44, .36, .40))]}),
]
N = int(round(SEG[-1][1] * FPS))
IW, IH = int(AW * .84), int(AH * .84); IX, IY = AX + (AW - IW) // 2 + 18, AY + (AH - IH) // 2; MI = rrect_mask(IW, IH, RAD)
frames_dir = None
enc = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-', '-i', AUDIO,
                        '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-preset', 'slow', '-crf', '15', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '256k',
                        '-shortest', '-movflags', '+faststart', OUT], stdin=subprocess.PIPE)
for t0, t1, c, sa, sp, fx in SEG:
    f0, f1 = int(round(t0 * FPS)), int(round(t1 * FPS)); n = f1 - f0
    assert sa + n / FPS * sp <= dur(c) + .05, (c, sa, sp, n)
    still = before_look(decode(c, sa, 1, BW, BH)[0])
    vid = decode(c, sa, n, AW, AH, sp)
    extra = {}
    if 'box' in fx: tb, cb, sb = fx['box']; extra['box'] = (tb, decode(cb, sb, f1 - int(round(tb * FPS)), AW, AH))
    if 'iris' in fx: ti, ci, si = fx['iris']; extra['iris'] = (ti, decode(ci, si, f1 - int(round(ti * FPS)), AW, AH))
    ins = [(ti, decode(ci, si, 12, IW, IH, 1., cr)) for ti, ci, si, cr in fx.get('inserts', [])]
    for k in range(n):
        t = (f0 + k) / FPS; fr = BASE.copy()
        paste(fr, still, BX, BY, MB)
        a = vid[k].copy()
        if 'relight' in fx: a = relight(a, np.clip((t - fx['relight']) / .22, 0, 1))
        if 'box' in extra:
            tb, bv = extra['box']; kb = int(round((t - tb) * FPS))
            if kb >= 0:   # a rounded window grows from the centre and becomes the frame
                u = min(1, kb / (.38 * FPS)); u = 1 - (1 - u) ** 3; w = int(AW * (.32 + .68 * u)); h = int(AH * (.32 + .68 * u))
                x0, y0 = (AW - w) // 2, (AH - h) // 2; m = rrect_mask(w, h, int(RAD * (1 - u) + 4))
                a[y0:y0 + h, x0:x0 + w] = a[y0:y0 + h, x0:x0 + w] * (1 - m) + bv[kb][y0:y0 + h, x0:x0 + w] * m
        if 'iris' in extra:
            ti, iv = extra['iris']; ki = int(round((t - ti) * FPS))
            if ki >= 0:   # a circle opens from off-centre and reveals the next room
                u = min(1, ki / (.2 * FPS)); u = u * u; R = 30 + u * 1250; cx, cy = AW * .6, AH * .5
                m = np.clip(R - np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) + .5, 0, 1)[..., None].astype(np.float32)
                a = a * (1 - m) + iv[ki] * m
        a = after_look(a)
        if fx.get('flash'): a = a + (1 - a) * max(0, 1 - t / .12)
        paste(fr, a, AX, AY, MA)
        for j, (ti, iv) in enumerate(ins):    # detail close-ups pop in on the beat, each until the next one
            tn = ins[j + 1][0] if j + 1 < len(ins) else t1
            if ti <= t < tn:
                ki = min(len(iv) - 1, int((t - ti) * FPS)); u = min(1, (t - ti) / .1); s = .9 + .1 * (1 - (1 - u) ** 3)
                img = after_look_ins = np.clip(iv[ki] * 1.0, 0, 1)
                if s < .999:
                    im = Image.fromarray((img * 255).astype(np.uint8)).resize((int(IW * s), int(IH * s)), Image.LANCZOS)
                    img = np.asarray(im, np.float32) / 255; m = rrect_mask(img.shape[1], img.shape[0], RAD)
                    paste(fr, img, IX + (IW - img.shape[1]) // 2, IY + (IH - img.shape[0]) // 2, m)
                else: paste(fr, img, IX, IY, MI)
        enc.stdin.write((np.clip(fr, 0, 1) * 255).astype(np.uint8).tobytes())
    print(f'{t0:5.2f}-{t1:5.2f} {c} done', flush=True)
enc.stdin.close(); enc.wait(); print('wrote', OUT)
