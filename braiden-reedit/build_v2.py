"""AVE re-edit of Braiden Shaw's clip, V2: follows the source reel's edit closely
(teal look, money wheel, engraving texture, coin, teal band with cut-out,
full-screen cut-aways, blur-zoom ending) with every graphic drawn here and
our own cut-away stills. Layout matches the source: raw on top, edit below;
the source's bottom card is left out.

Usage:
    python build.py prep SOURCE.mp4 WORK          # raw frames, voice (see build.py)
    # WORK/mask/NNNN.png  cut-outs for every frame (u2net_human_seg)
    # WORK/broll/{car,house,jetski}.jpg  our cut-away stills
    # WORK/fonts/{PlayfairItalic,Urbanist}.ttf
    python build_v2.py render SOURCE.mp4 WORK [MUSIC.mp3 START]
    python build_v2.py stills SOURCE.mp4 WORK 1.0 7.6 ...
"""
import math, os, subprocess, sys
from functools import lru_cache

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
import importlib.util  # noqa: E402
_spec = importlib.util.spec_from_file_location("braiden_build", os.path.join(HERE, "build.py"))
b1 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(b1)   # also puts before-after-reel on sys.path
from build_v3 import expo, spring, smooth, clamp01, place  # noqa: E402
v1 = b1.v1

W, H, FPS = 1080, 1920, 30
PW, PH = 1080, 608
RAW_Y, EDIT_Y = 0, 615            # same stacking as the source reel (x1.5)
N, END = b1.N, b1.END

TEAL = (22, 140, 150)
TEAL_D = (12, 92, 100)
TEAL_L = (70, 215, 222)
WHITE = (255, 255, 255)
INK = (10, 12, 14)

WORK = None


@lru_cache(None)
def font(kind, size):
    fd = os.path.join(WORK, "fonts")
    if kind.startswith("serif"):
        f = ImageFont.truetype(os.path.join(fd, "PlayfairItalic.ttf"), size); f.set_variation_by_axes([int(kind[5:] or 800)])
        return f
    f = ImageFont.truetype(os.path.join(fd, "Urbanist.ttf"), size); f.set_variation_by_axes([int(kind[3:])])
    return f


@lru_cache(None)
def word(s, kind, size, color):
    f = font(kind, size)
    asc, desc = f.getmetrics()
    im = Image.new("RGBA", (int(f.getlength(s)) + 16, asc + desc + 6), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((6, 2), s, font=f, fill=color + (255,))
    bb = im.getbbox() or (0, 0, 1, 1)
    return im.crop((bb[0], 0, bb[2], im.height))


def glow(im, radius=10, strength=0.9, color=None):
    a = im.getchannel("A").filter(ImageFilter.GaussianBlur(radius))
    g = Image.new("RGBA", im.size, (color or TEAL_L) + (0,))
    g.putalpha(a.point(lambda v: int(v * strength)))
    out = Image.new("RGBA", im.size, (0, 0, 0, 0)); out.alpha_composite(g); out.alpha_composite(im)
    return out


def pad(im, p):
    o = Image.new("RGBA", (im.width + 2 * p, im.height + 2 * p), (0, 0, 0, 0)); o.alpha_composite(im, (p, p)); return o


# ---- our graphics -----------------------------------------------------------------
@lru_cache(None)
def banknote(w=220, h=100):
    S = 3
    im = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w * S - 1, h * S - 1), 8 * S, fill=TEAL + (235,), outline=TEAL_L + (255,), width=2 * S)
    d.rounded_rectangle((8 * S, 8 * S, (w - 8) * S, (h - 8) * S), 6 * S, outline=TEAL_L + (150,), width=S)
    d.ellipse(((w / 2 - 26) * S, (h / 2 - 26) * S, (w / 2 + 26) * S, (h / 2 + 26) * S), outline=TEAL_L + (255,), width=2 * S)
    f = font("serif800", 40 * S)
    d.text((w / 2 * S, h / 2 * S), "$", font=f, fill=(210, 255, 255, 255), anchor="mm")
    for cx in (34, w - 34):
        d.text((cx * S, h / 2 * S), "100", font=font("urb700", 16 * S), fill=TEAL_L + (230,), anchor="mm")
    return im.resize((w, h), Image.LANCZOS)


@lru_cache(None)
def money_wheel(r=120):
    size = r * 2 + 260
    wheel = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    note = banknote(170, 76)
    c = size / 2
    for k in range(26):
        ang = k * (360 / 26)
        n = note.rotate(-ang, resample=Image.BICUBIC, expand=True)
        a = math.radians(ang)
        x = c + r * math.cos(a) - n.width / 2
        y = c + r * math.sin(a) - n.height / 2
        wheel.alpha_composite(n, (int(x), int(y)))
    return glow(wheel, 18, 0.7)


@lru_cache(None)
def coin_face(r=90):
    S = 3
    im = Image.new("RGBA", (r * 2 * S, r * 2 * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((0, 0, r * 2 * S - 1, r * 2 * S - 1), fill=TEAL + (255,))
    d.ellipse((10 * S, 10 * S, (2 * r - 10) * S, (2 * r - 10) * S), outline=TEAL_L + (255,), width=4 * S)
    d.text((r * S, r * S), "$", font=font("serif900", int(r * 1.15) * S), fill=(215, 255, 255, 255), anchor="mm")
    return im.resize((2 * r, 2 * r), Image.LANCZOS)


def coin(t, r=90):
    """Spinning coin: squash the face horizontally, with a darker rim for depth."""
    c = math.cos(t * 4.2)
    face = coin_face(r)
    w = max(4, int(2 * r * abs(c)))
    f = face.resize((w, 2 * r), Image.LANCZOS)
    if c < 0:
        f = f.transpose(Image.FLIP_LEFT_RIGHT)
    edge = int(12 * (1 - abs(c))) + 2
    out = Image.new("RGBA", (2 * r + 30, 2 * r + 30), (0, 0, 0, 0))
    rim = Image.new("RGBA", (w + edge, 2 * r), (0, 0, 0, 0))
    ImageDraw.Draw(rim).ellipse((0, 0, w + edge - 1, 2 * r - 1), fill=TEAL_D + (255,))
    out.alpha_composite(rim, ((out.width - w) // 2 - edge // 2 + 3, 15))
    out.alpha_composite(f, ((out.width - w) // 2, 15))
    return glow(pad(out, 30), 22, 0.85)


@lru_cache(None)
def engraving():
    """Banknote-style guilloche line texture (our own, procedural)."""
    S = 2
    w, h = PW * S, PH * S
    im = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(im)
    cx, cy = w * 0.78, h * 0.62
    for k in range(70):
        r0 = 30 * S + k * 9 * S
        pts = []
        for j in range(0, 361, 3):
            a = math.radians(j)
            rr = r0 + 6 * S * math.sin(a * 9 + k * 0.35) + 3 * S * math.sin(a * 23 - k * 0.2)
            pts.append((cx + rr * math.cos(a) * 1.15, cy + rr * math.sin(a)))
        d.line(pts, fill=255, width=S)
    for k in range(60):
        y0 = k * 22 * S
        pts = [(x, y0 + 10 * S * math.sin(x / (40 * S) + k * 0.4)) for x in range(0, w, 8)]
        d.line(pts, fill=110, width=S)
    im = im.resize((PW, PH), Image.LANCZOS)
    a = np.asarray(im).astype(np.float32) / 255
    xx = np.linspace(0, 1, PW)[None, :]
    a *= np.clip((xx - 0.35) / 0.35, 0, 1)   # mostly on the right, like the source
    return a


@lru_cache(None)
def dot_grid():
    a = np.zeros((PH, PW), np.float32)
    for y in range(8, PH, 18):
        for x in range(8, PW, 18):
            cv2.circle(a, (x, y), 2, 1.0, -1, lineType=cv2.LINE_AA)
    return a


class Renderer:
    def __init__(self, work):
        global WORK
        WORK = work
        self.work = work
        self.broll = {k: Image.open(os.path.join(work, "broll", k + ".jpg")).convert("RGB") for k in ("car", "house", "jetski")}
        yy, xx = np.mgrid[0:PH, 0:PW].astype(np.float32)
        self.vig = (1 - 0.32 * np.clip(((xx - PW / 2) / (PW * 0.6)) ** 2 + ((yy - PH / 2) / (PH * 0.7)) ** 2, 0, 1))[..., None]

    def raw(self, i):
        return Image.open(os.path.join(self.work, "raw", f"{min(max(i, 1), N):04d}.jpg")).convert("RGB")

    def mask(self, i):
        p = os.path.join(self.work, "mask", f"{min(max(i, 1), N):04d}.png")
        return np.asarray(Image.open(p).convert("L")).astype(np.float32) / 255

    # framing: returns crop box in source pixels
    def box(self, t):
        if t < 0.5:
            k = 1.75 - 0.25 * smooth(t / 0.5); cx, cy = 0.40, 0.30
        elif t < 3.13:
            k = 1.0 + 0.05 * smooth((t - 0.5) / 2.6); cx, cy = 0.45, 0.4
        elif t < 8.77:
            k = 1.04 + 0.05 * smooth((t - 3.13) / 5.6); cx, cy = 0.4, 0.4
        elif t < 14.45:
            k = 1.0 + 0.06 * smooth((t - 8.77) / 1.8); cx, cy = 0.5, 0.45
        elif t < 15.0:
            k = 1.9 - 0.85 * expo((t - 14.45) / 0.55); cx, cy = 0.5, 0.35
        else:
            k = 1.05 + 0.04 * smooth((t - 15.0) / 2.6); cx, cy = 0.5, 0.45
        cw, ch = PW / k, PH / k
        x0 = min(max(cx * PW - cw * cx, 0), PW - cw); y0 = min(max(cy * PH - ch * cy, 0), PH - ch)
        return (x0, y0, x0 + cw, y0 + ch)

    def grade(self, a):
        """Teal-orange: teal in the shadows, warm skin, a little contrast."""
        lum = a.mean(2, keepdims=True)
        sh = np.clip(1 - lum * 2.2, 0, 1)
        a = a + sh * (np.array(TEAL, np.float32) / 255 - 0.3) * 0.07
        a = np.clip(a * 1.06 + 0.01, 0, 1)
        return np.clip(a * self.vig, 0, 1)

    def frame_edit(self, i, t):
        for a, b, key in ((10.54, 11.08, "car"), (11.08, 11.62, "house"), (11.62, 14.45, "jetski")):
            if a <= t < b:
                return self.cutaway(key, t - a, b - a)
        bx = self.box(t)
        src = np.asarray(self.raw(i).resize((PW, PH), Image.BICUBIC, box=bx)).astype(np.float32) / 255
        m = np.asarray(Image.fromarray((self.mask(i) * 255).astype(np.uint8)).resize((PW, PH), Image.BILINEAR, box=bx)).astype(np.float32) / 255
        m = cv2.GaussianBlur(m, (0, 0), 1.0)
        img = self.grade(src)
        bg_layers = Image.new("RGBA", (PW, PH), (0, 0, 0, 0))   # things that sit behind him
        fg = Image.new("RGBA", (PW, PH), (0, 0, 0, 0))          # things in front
        teal = np.array(TEAL_L, np.float32) / 255

        if t < 0.5:   # punch-in intro: dot grid + floating note behind him
            g = dot_grid() * 0.55 * (1 - m)
            img = img * (1 - g[..., None] * 0.5) + teal * g[..., None] * 0.5
            n = glow(pad(banknote(260, 118), 30), 18, 0.8)
            place(bg_layers, n.rotate(-8, resample=Image.BICUBIC, expand=True), 250, 210, anchor="c")
            mc = word("Money can buy", "urb600", 64, WHITE)
            place(fg, mc, -mc.width + (mc.width + 30) * expo(t / 0.5) - 10, 80)
        elif t < 3.13:
            wh = money_wheel()
            p = expo((t - 0.5) / 0.6)
            place(bg_layers, wh.rotate(-(t - 0.5) * 22, resample=Image.BICUBIC), PW * 0.60, PH * 0.27,
                  scale=0.75 + 0.25 * p, alpha=p, anchor="c")
            pm = expo((t - 0.5) / 0.4)
            mc = word("Money can buy", "urb600", 46, WHITE)
            place(fg, mc, 70 + (1 - pm) * -60, 172, alpha=pm)
            if t >= 1.30:
                q = expo((t - 1.30) / 0.45)
                hp = word("Happiness", "serif800", 86, WHITE)
                bw = int((hp.width + 70) * q)
                d = ImageDraw.Draw(fg)
                d.rectangle((0, 226, bw, 226 + 98), fill=TEAL + (235,))
                place(fg, hp, 34 - (1 - q) * 80, 224, alpha=q)
            if t >= 2.04:
                s = "I'm gonna stand by that"
                n_ch = int(len(s) * clamp01((t - 2.04) / 0.9))
                place(fg, word(s[:max(n_ch, 1)], "urb500", 26, (225, 235, 235)), 72, 346, alpha=1.0 if n_ch else 0)
        elif t < 6.40:
            e = engraving()
            p = smooth((t - 3.13) / 0.5)
            img = img * (1 - e[..., None] * 0.55 * p) + (np.array(TEAL_D, np.float32) / 255 * 0.0 + teal * 0.55) * e[..., None] * 0.55 * p
            if t >= 4.90:
                q = spring(t - 4.90, 12, 0.6)
                place(bg_layers, coin(t), PW * 0.80, PH * 0.34, scale=max(q, 0.01), anchor="c")
            if t >= 5.42:
                x = PW * 0.70
                for st, wd in ((5.42, "we"), (5.52, "spend"), (5.78, "it"), (5.92, "on")):
                    w_ = word(wd, "urb600", 46, WHITE)
                    q = expo((t - st) / 0.3)
                    if q > 0:
                        place(fg, w_, x, PH * 0.56 + (1 - q) * 14, alpha=q, blur=(1 - q) * 4)
                    x += w_.width + 12
        elif t < 8.77:
            e = engraving()
            img = img * (1 - e[..., None] * 0.55) + teal * e[..., None] * 0.30
            p = expo((t - 6.40) / 0.45)
            bh = int(PH * 0.45)
            band = Image.new("RGBA", (PW, PH), (0, 0, 0, 0))
            ImageDraw.Draw(band).rectangle((0, 0, PW, int(bh * p)), fill=TEAL + (255,))
            bg_layers.alpha_composite(band)
            x = PW * 0.47
            for st, wd in ((6.48, "are"), (6.58, "the"), (6.72, "worst"), (7.10, "at"), (7.34, "buying")):
                w_ = word(wd, "urb500", 48, WHITE)
                q = expo((t - st) / 0.3)
                if q > 0:
                    place(fg, w_, x, 92 + (1 - q) * 14, alpha=q, blur=(1 - q) * 4)
                x += w_.width + 12
            if t >= 7.82:
                q = expo((t - 7.82) / 0.45)
                hp = word("Happiness", "serif800", 92, WHITE)
                bx0 = PW * 0.47 - 30
                d = ImageDraw.Draw(fg)
                d.rectangle((bx0, 160, bx0 + (hp.width + 60) * q, 160 + 110), fill=TEAL_D + (255,))
                place(fg, hp, bx0 + 30 + (1 - q) * 40, 160, alpha=q)
        elif t >= 15.0:
            # bottom captions, "happiness" in teal serif
            y1, y2 = PH - 150, PH - 86
            row1 = [(15.44, "Have", "urb700"), (15.78, "that", "urb700"), (15.98, "happiness", "serif800")]
            row2 = [(16.46, "that", "urb700"), (16.76, "can", "urb700"), (16.92, "come", "urb700"),
                    (17.12, "from", "urb700"), (17.30, "it", "urb700")]
            for row, y in ((row1, y1), (row2, y2)):
                ims = [word(wd, k, 52 if k != "serif800" else 58, WHITE if k != "serif800" else TEAL_L) for _, wd, k in row]
                tw = sum(im.width for im in ims) + 12 * (len(ims) - 1)
                x = (PW - tw) / 2
                for (st, wd, k), im in zip(row, ims):
                    q = expo((t - st + 0.03) / 0.3)
                    if q > 0:
                        place(fg, glow(pad(im, 14), 10, 0.5, (0, 0, 0)), x - 14, y - 14 + (1 - q) * 16 - (6 if k == "serif800" else 0),
                              alpha=q, blur=(1 - q) * 4)
                    x += im.width + 12

        # composite: background layers sit behind him (masked), foreground on top
        bga = np.asarray(bg_layers).astype(np.float32) / 255
        if bga[..., 3].any():
            al = bga[..., 3:4] * (1 - m[..., None])
            img = img * (1 - al) + bga[..., :3] * al
        out = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)).convert("RGBA")
        if 6.40 <= t < 8.77:   # white cut-out outline where he crosses the band
            mm = (m > 0.5).astype(np.uint8)
            ring = cv2.dilate(mm, np.ones((7, 7), np.uint8)) - mm
            bh = int(PH * 0.45 * expo((t - 6.40) / 0.45))
            ring[bh:] = 0
            ra = cv2.GaussianBlur(ring.astype(np.float32), (0, 0), 0.8)
            rl = Image.new("RGBA", (PW, PH), WHITE + (0,)); rl.putalpha(Image.fromarray((ra * 255).astype(np.uint8)))
            out.alpha_composite(rl)
        out.alpha_composite(fg)
        if 14.45 <= t < 15.0:   # blur-zoom into the closing shot
            out = out.filter(ImageFilter.GaussianBlur(14 * (1 - expo((t - 14.45) / 0.55))))
        return out

    def cutaway(self, key, dt, dur):
        im = self.broll[key]
        w, h = im.size
        if key == "car":
            k, cx, cy = 1.12 - 0.08 * dt / dur, 0.55, 0.6
        elif key == "house":
            k, cx, cy = 1.0 + 0.10 * dt / dur, 0.5, 0.45
        else:
            k, cx, cy = 1.35, 0.55 + 0.12 * dt / dur, 0.62     # pan with the jet ski
        cw, ch = w / k, h / k
        x0 = min(max(cx * w - cw / 2, 0), w - cw); y0 = min(max(cy * h - ch / 2, 0), h - ch)
        fr = im.resize((PW, PH), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))
        a = np.asarray(fr).astype(np.float32) / 255
        a = np.clip((a - 0.02) * 1.05, 0, 1) * self.vig
        if key == "jetski":   # a little water shimmer so the still breathes
            yy = np.arange(PH)[:, None]
            a = np.clip(a + 0.025 * np.sin(yy / 6 + dt * 9)[..., None] * (yy > PH * 0.35)[..., None], 0, 1)
        out = Image.fromarray((a * 255).astype(np.uint8)).convert("RGBA")
        if dt < 0.12:   # whip in
            arr = cv2.blur(np.asarray(out.convert("RGB")), (int(1 + 70 * (1 - dt / 0.12)) | 1, 1))
            out = Image.fromarray(arr).convert("RGBA")
        return out

    def frame(self, fi):
        t = fi / FPS
        i = fi + 1
        page = Image.new("RGB", (W, H), (0, 0, 0))
        page.paste(self.raw(i).resize((PW, PH + 1), Image.LANCZOS), (0, RAW_Y))
        ed = self.frame_edit(i, t).convert("RGB")
        if any(abs(t - b) < 0.08 for b in (0.5, 3.13, 8.77)):
            pass
        page.paste(ed, (0, EDIT_Y))
        return np.asarray(page)


SFX = ([(t, "whoosh") for t in (0.50, 10.54, 11.08, 11.62, 14.45)]
       + [(1.30, "thock"), (4.90, "bloop"), (6.40, "whoosh"), (7.82, "thock"), (15.98, "bloop")])

R = None


def _init(work):
    global R
    R = Renderer(work)


def _frame(fi):
    return R.frame(fi).tobytes()


def render(work, music=None, start=0.0, only=None):
    from multiprocessing import Pool
    if only is not None:
        _init(work)
        for fi in only:
            Image.fromarray(R.frame(fi)).save(os.path.join(work, f"v2_{fi:04d}.png"))
        return
    vid = os.path.join(work, "video_v2.mp4")
    p = subprocess.Popen(f'ffmpeg -v error -y -f rawvideo -pix_fmt rgb24 -s {W}x{H} -r {FPS} -i - '
                         f'-c:v libx264 -preset slow -crf 15 -pix_fmt yuv420p "{vid}"', shell=True, stdin=subprocess.PIPE)
    with Pool(3, initializer=_init, initargs=(work,)) as pool:
        for buf in pool.imap(_frame, range(N), chunksize=4):
            p.stdin.write(buf)
    p.stdin.close(); p.wait()
    b1.SFX[:] = SFX
    mix, master = os.path.join(work, "mix_v2.wav"), os.path.join(work, "master_v2.wav")
    b1.build_audio(work, mix, music, start)
    v1.loudnorm(mix, master)
    out = os.path.join(work, "AVE_Braiden_Reedit_V2.mp4")
    v1.sh(f'ffmpeg -v error -y -i "{vid}" -i "{master}" -c:v copy -c:a aac -b:a 256k -shortest -movflags +faststart "{out}"')
    print(out)


if __name__ == "__main__":
    cmd, src, work = sys.argv[1:4]
    if cmd == "render":
        render(work, sys.argv[4] if len(sys.argv) > 4 else None, float(sys.argv[5]) if len(sys.argv) > 5 else 0.0)
    elif cmd == "stills":
        render(work, only=[int(round(float(x) * FPS)) for x in sys.argv[4:]])
