"""AVE Studio · full-screen SaaS-style talking head (Braiden Shaw clip).

Editing style taken from the user's reference (not its layout or graphics):
clean bright studio, person cut out and centred low, a huge word over him,
camera pull-backs as glossy 3D cards fly in with glow and motion blur,
one-frame inverted silhouette flashes on hits, a light arc whipping around the
cards, sparkle crosses, small sentence-case lines typed word by word, glowing
keywords with pixel glitches, whip transitions. AVE colours: lime / ink / off-white.

Needs the WORK dir from build.py / build_v2.py (raw/, mask/, voice.wav, words.json, broll/).
Usage: python build_saas_full.py render SOURCE.mp4 WORK [MUSIC.mp3 START]
       python build_saas_full.py stills SOURCE.mp4 WORK 1.0 ...
"""
import json, math, os, subprocess, sys
from functools import lru_cache

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
import importlib.util  # noqa: E402
_spec = importlib.util.spec_from_file_location("braiden_build", os.path.join(HERE, "build.py"))
b1 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(b1)
v1 = b1.v1
from build_v3 import expo, spring, smooth, clamp01, place  # noqa: E402

W, H, FPS = 1080, 1920, 30
N, END = b1.N, b1.END
INK, PAPER, LIME = (14, 14, 14), (243, 242, 238), (200, 255, 46)
OLIVE, DEEP = (110, 150, 10), (60, 84, 4)
G300, G500 = (214, 212, 205), (138, 135, 127)
WHITE = (255, 255, 255)
FONTS = os.path.join(b1.ROOT, "ave-promo", "film", "fonts")
SHOTS = [(0.0, 3.13), (3.13, 8.77), (8.77, END)]
FLASH = [1.30, 3.10, 7.76, 8.74, 10.50, 15.92]      # 2-frame inverted silhouette flashes
WHIP = [3.13, 8.77]


@lru_cache(None)
def font(kind, size):
    files = {"xb": "InterDisplay-ExtraBold.otf", "b": "InterDisplay-Bold.otf", "sb": "InterDisplay-SemiBold.otf",
             "md": "InterDisplay-Medium.otf", "serif": "InstrumentSerif-italic-400.woff2", "mono": "JetBrainsMono-normal-500.woff2"}
    return ImageFont.truetype(os.path.join(FONTS, files[kind]), size)


@lru_cache(None)
def txt(s, kind, size, color, track=0.0):
    f = font(kind, size)
    asc, desc = f.getmetrics()
    ws = [f.getlength(c) for c in s]
    tr = track * size
    im = Image.new("RGBA", (int(sum(ws) + tr * len(s)) + 20, asc + desc + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if track:
        x = 4
        for c, cw in zip(s, ws):
            d.text((x, 4), c, font=f, fill=color + (255,)); x += cw + tr
    else:
        d.text((4, 4), s, font=f, fill=color + (255,))
    bb = im.getbbox() or (0, 0, 1, 1)
    return im.crop((bb[0], 0, bb[2], im.height))


def rmask(w, h, r, ss=3):
    m = Image.new("L", (w * ss, h * ss), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w * ss - 1, h * ss - 1), r * ss, fill=255)
    return m.resize((w, h), Image.LANCZOS)


def pad(im, p):
    o = Image.new("RGBA", (im.width + 2 * p, im.height + 2 * p), (0, 0, 0, 0)); o.alpha_composite(im, (p, p)); return o


def glow(im, color, radius, strength, p=None):
    p = p if p is not None else radius * 2
    im = pad(im, p)
    a = im.getchannel("A").filter(ImageFilter.GaussianBlur(radius))
    g = Image.new("RGBA", im.size, color + (0,)); g.putalpha(a.point(lambda v: int(min(255, v * strength))))
    out = Image.new("RGBA", im.size, (0, 0, 0, 0)); out.alpha_composite(g); out.alpha_composite(im)
    return out


def drop_shadow(im, blur=22, a=0.22, oy=24):
    p = blur * 2
    im = pad(im, p)
    s = Image.new("RGBA", im.size, (30, 34, 18, 0))
    s.putalpha(im.getchannel("A").filter(ImageFilter.GaussianBlur(blur)).point(lambda v: int(v * a)))
    out = Image.new("RGBA", im.size, (0, 0, 0, 0)); out.alpha_composite(s, (0, oy)); out.alpha_composite(im)
    return out


def persp(im, ry=0.0, rx=0.0, rz=0.0):
    """Tilt a flat card in 3D (degrees) with a simple perspective projection."""
    w, h = im.size
    f = 1.6 * max(w, h)
    pts = np.array([[-w / 2, -h / 2, 0], [w / 2, -h / 2, 0], [w / 2, h / 2, 0], [-w / 2, h / 2, 0]], np.float32)
    a, b, c = math.radians(rx), math.radians(ry), math.radians(rz)
    Rx = np.array([[1, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]])
    Ry = np.array([[math.cos(b), 0, math.sin(b)], [0, 1, 0], [-math.sin(b), 0, math.cos(b)]])
    Rz = np.array([[math.cos(c), -math.sin(c), 0], [math.sin(c), math.cos(c), 0], [0, 0, 1]])
    P = pts @ (Rz @ Ry @ Rx).T
    P[:, 2] += f
    proj = np.stack([P[:, 0] * f / P[:, 2], P[:, 1] * f / P[:, 2]], 1)
    proj -= proj.min(0)
    ow, oh = int(proj[:, 0].max()) + 2, int(proj[:, 1].max()) + 2
    M = cv2.getPerspectiveTransform(np.float32([[0, 0], [w, 0], [w, h], [0, h]]), proj.astype(np.float32))
    arr = cv2.warpPerspective(np.asarray(im), M, (ow, oh), flags=cv2.INTER_LINEAR)
    return Image.fromarray(arr)


def vblur(im, px):
    if px < 2:
        return im
    a = np.asarray(im).astype(np.float32)
    k = int(px) | 1
    a = cv2.blur(a, (1, k))
    return Image.fromarray(a.clip(0, 255).astype(np.uint8))


def gradient_word(s, size, top, bottom, kind="xb"):
    im = txt(s, kind, size, WHITE)
    a = np.asarray(im.getchannel("A")).astype(np.float32)
    y = np.linspace(0, 1, im.height)[:, None, None]
    col = np.array(top, np.float32) * (1 - y) + np.array(bottom, np.float32) * y
    out = np.dstack([np.broadcast_to(col, a.shape + (3,)), a[..., None]])
    return Image.fromarray(out.clip(0, 255).astype(np.uint8), "RGBA")


# ---- 3D-looking cards (our own) -------------------------------------------------------
@lru_cache(None)
def gloss_tile(kind, size=300):
    """Rounded glossy tile with a thick side for depth (lime '$' tile, bank card)."""
    S = 2
    w, h = (size, size) if kind == "dollar" else (int(size * 1.58), size)
    depth = 18
    im = Image.new("RGBA", ((w + 10) * S, (h + depth + 10) * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    r = 58 if kind == "dollar" else 40
    d.rounded_rectangle((0, depth * S, w * S, (h + depth) * S), r * S, fill=DEEP + (255,))
    face = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
    yy = np.linspace(0, 1, h * S)[:, None, None]
    col = np.array((222, 255, 120), np.float32) * (1 - yy) + np.array(OLIVE, np.float32) * yy * 0.55 + np.array(LIME, np.float32) * yy * 0.45
    arr = np.dstack([np.broadcast_to(col, (h * S, w * S, 3)), np.full((h * S, w * S, 1), 255.0)])
    face = Image.fromarray(arr.astype(np.uint8), "RGBA"); face.putalpha(rmask(w * S, h * S, r * S, 1))
    im.alpha_composite(face, (0, 0))
    fd = ImageDraw.Draw(im)
    if kind == "dollar":
        fd.text((w * S / 2, h * S / 2 - 8 * S), "$", font=font("xb", int(size * 0.72) * S), fill=WHITE + (255,), anchor="mm")
        fd.rounded_rectangle((w * S * .32, h * S * .78, w * S * .68, h * S * .88), 20 * S, fill=(255, 255, 255, 120))
    else:
        fd.rounded_rectangle((40 * S, 70 * S, 110 * S, 120 * S), 10 * S, fill=(240, 220, 120, 255))
        fd.text((40 * S, h * S - 90 * S), "••••  ••••  7800", font=font("mono", 34 * S), fill=INK + (230,))
        fd.text((40 * S, h * S - 46 * S), "PLATINUM", font=font("mono", 22 * S), fill=INK + (170,))
    # gloss highlight
    gl = Image.new("L", (w * S, h * S), 0)
    ImageDraw.Draw(gl).ellipse((-w * S * .3, -h * S * .9, w * S * .9, h * S * .45), fill=90)
    gl = gl.filter(ImageFilter.GaussianBlur(30 * S))
    gm = np.minimum(np.asarray(gl), np.asarray(rmask(w * S, h * S, r * S, 1)))
    gw = Image.new("RGBA", (w * S, h * S), WHITE + (0,)); gw.putalpha(Image.fromarray(gm))
    im.alpha_composite(gw, (0, 0))
    fd.rounded_rectangle((2 * S, 2 * S, w * S - 2 * S, h * S - 2 * S), r * S, outline=(255, 255, 255, 160), width=3 * S)
    return im.resize((im.width // S, im.height // S), Image.LANCZOS)


@lru_cache(None)
def photo_card(key, title, sub, work, w=360, h=470):
    S = 2
    im = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
    body = Image.new("RGBA", (w * S, h * S), (245, 247, 240, 235)); body.putalpha(rmask(w * S, h * S, 44 * S, 1))
    im.alpha_composite(body)
    ph = Image.open(os.path.join(work, "broll", key + ".jpg")).convert("RGB")
    pw_, phh = (w - 36) * S, int(h * 0.56) * S
    cw = int(ph.height * pw_ / phh)
    x0 = max(0, (ph.width - cw) // 2)
    ph = ph.crop((x0, 0, x0 + min(cw, ph.width), ph.height)).resize((pw_, phh), Image.LANCZOS).convert("RGBA")
    ph.putalpha(rmask(pw_, phh, 30 * S, 1))
    im.alpha_composite(ph, (18 * S, 18 * S))
    d = ImageDraw.Draw(im)
    d.text((26 * S, (h * 0.56 + 40) * S), title, font=font("xb", 46 * S), fill=INK + (255,))
    d.text((26 * S, (h * 0.56 + 100) * S), sub, font=font("md", 24 * S), fill=G500 + (255,))
    # tag + check badge
    d.rounded_rectangle((26 * S, 30 * S, 128 * S, 66 * S), 18 * S, fill=(255, 255, 255, 230))
    d.text((40 * S, 36 * S), "Saved", font=font("sb", 22 * S), fill=INK + (255,))
    d.rounded_rectangle(((w - 74) * S, (h - 74) * S, (w - 22) * S, (h - 22) * S), 16 * S, fill=LIME + (255,))
    d.line([((w - 62) * S, (h - 48) * S), ((w - 52) * S, (h - 37) * S), ((w - 34) * S, (h - 60) * S)], fill=INK + (255,), width=5 * S)
    d.rounded_rectangle((2 * S, 2 * S, (w - 2) * S, (h - 2) * S), 44 * S, outline=(255, 255, 255, 255), width=3 * S)
    return im.resize((w, h), Image.LANCZOS)


@lru_cache(None)
def item_card(kind, label, price, w=230, h=290):
    S = 2
    im = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
    body = Image.new("RGBA", (w * S, h * S), (250, 251, 246, 240)); body.putalpha(rmask(w * S, h * S, 36 * S, 1))
    im.alpha_composite(body)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((16 * S, 16 * S, (w - 16) * S, 170 * S), 26 * S, fill=(232, 242, 205, 255))
    c = INK + (255,); lw = 7 * S
    cx, cy = w * S / 2, 93 * S
    if kind == "bag":
        d.rounded_rectangle((cx - 50 * S, cy - 20 * S, cx + 50 * S, cy + 55 * S), 14 * S, outline=c, width=lw)
        d.arc((cx - 28 * S, cy - 55 * S, cx + 28 * S, cy + 5 * S), 180, 360, fill=c, width=lw)
    elif kind == "watch":
        d.rounded_rectangle((cx - 20 * S, cy - 70 * S, cx + 20 * S, cy + 70 * S), 8 * S, outline=c, width=lw)
        d.ellipse((cx - 44 * S, cy - 44 * S, cx + 44 * S, cy + 44 * S), fill=(255, 255, 255, 255), outline=c, width=lw)
        d.line((cx, cy, cx, cy - 26 * S), fill=c, width=lw); d.line((cx, cy, cx + 18 * S, cy + 10 * S), fill=c, width=lw)
    else:
        d.line([(cx - 70 * S, cy + 30 * S), (cx - 70 * S, cy - 25 * S), (cx - 30 * S, cy - 25 * S), (cx + 5 * S, cy + 5 * S),
                (cx + 70 * S, cy + 12 * S), (cx + 72 * S, cy + 40 * S), (cx - 70 * S, cy + 40 * S), (cx - 70 * S, cy + 30 * S)],
               fill=c, width=lw, joint="curve")
    d.text((22 * S, 190 * S), label, font=font("b", 34 * S), fill=INK + (255,))
    d.text((22 * S, 236 * S), price, font=font("md", 28 * S), fill=G500 + (255,))
    return im.resize((w, h), Image.LANCZOS)


@lru_cache(None)
def sparkle(size=40):
    S = 4
    im = Image.new("RGBA", (size * S, size * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    m = size * S / 2; t = size * S * 0.09
    d.rectangle((m - t, 0, m + t, size * S), fill=INK + (255,)); d.rectangle((0, m - t, size * S, m + t), fill=INK + (255,))
    return im.resize((size, size), Image.LANCZOS).rotate(0)


# ===========================================================================
class Renderer:
    def __init__(self, work):
        self.work = work
        self.words = json.load(open(os.path.join(work, "words.json")))
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.sqrt(((xx - W / 2) / (W * 0.9)) ** 2 + ((yy - H * 0.42) / (H * 0.7)) ** 2)
        bg = np.array((250, 250, 247), np.float32) * (1 - r[..., None] * 0.07) + np.array((228, 228, 222), np.float32) * r[..., None] * 0.07
        self.bg = Image.fromarray(bg.clip(0, 255).astype(np.uint8)).convert("RGBA")
        self.shot_geo = self.shot_geometry()

    def raw(self, i):
        return Image.open(os.path.join(self.work, "raw", f"{min(max(i, 1), N):04d}.jpg")).convert("RGB")

    def mask(self, i):
        return Image.open(os.path.join(self.work, "mask", f"{min(max(i, 1), N):04d}.png")).convert("L")

    def shot_geometry(self):
        """Per shot: scale so his shoulders are ~640 px wide, anchored on the median mask box."""
        geo = []
        for a, b in SHOTS:
            boxes = []
            for i in range(int(a * FPS) + 1, int(b * FPS) + 1, 6):
                m = np.asarray(self.mask(i)) > 128
                ys, xs = np.where(m)
                if len(xs):
                    boxes.append((np.percentile(xs, 2), np.percentile(xs, 98), ys.min(), ys.max()))
            bx = np.median(np.array(boxes), 0)
            s = 640 / (bx[1] - bx[0])
            geo.append((s, (bx[0] + bx[1]) / 2, bx[2], bx[3]))
        return geo

    # ---- person layer -------------------------------------------------------------
    def person(self, i, t):
        k = next(n for n, (a, b) in enumerate(SHOTS) if a <= t < b or n == len(SHOTS) - 1)
        s, cx, top, bot = self.shot_geo[k]
        im = self.raw(i); m = self.mask(i)
        w, h = int(1080 * s), int(608 * s)
        im = im.resize((w, h), Image.BICUBIC); m = m.resize((w, h), Image.BILINEAR)
        rgba = im.convert("RGBA")
        ma = np.asarray(m).astype(np.float32)
        ma = cv2.GaussianBlur(np.clip((ma - 30) / 200, 0, 1), (0, 0), 1.2)
        yy = np.arange(h)[:, None]
        cut = bot * s
        ma *= np.clip((cut - yy) / (0.14 * h), 0, 1)       # fade out above the desk line
        # bright, clean grade for the white set
        arr = np.asarray(rgba).astype(np.float32)
        arr[..., :3] = np.clip(arr[..., :3] * 1.14 + 6, 0, 255)
        arr[..., 3] = ma * 255
        out = Image.fromarray(arr.astype(np.uint8), "RGBA")
        # world placement: shoulders centred, desk line at y=1880
        ox = W / 2 - cx * s
        oy = 1880 - cut
        return out, ox, oy, ma

    # ---- camera ---------------------------------------------------------------------
    def zoom(self, t):
        keys = [(0.0, 1.42), (1.25, 1.42), (1.62, 0.96), (3.04, 0.90), (3.13, 1.30), (3.5, 1.04), (6.40, 1.0),
                (6.7, 0.94), (8.70, 0.92), (8.77, 1.28), (9.15, 0.98), (10.4, 0.96), (10.7, 0.86), (12.2, 0.86),
                (14.4, 1.0), (15.9, 1.0), (16.2, 1.08), (END, 1.12)]
        for (a, za), (b, zb) in zip(keys[:-1], keys[1:]):
            if a <= t < b:
                return za + (zb - za) * (expo((t - a) / (b - a)) if zb < za else smooth((t - a) / (b - a)))
        return keys[-1][1]

    def punch(self, t):
        k = 1.0
        for t0, amt in ((4.90, .05), (7.82, .05), (10.24, .05), (13.92, .04), (15.98, .06)):
            d = t - t0
            if 0 <= d < 1.0:
                k += amt * expo(d / 0.1) * (1 - smooth((d - 0.12) / 0.8))
        return k

    # ---- frame -------------------------------------------------------------------------
    def frame(self, fi):
        t = fi / FPS
        i = fi + 1
        z = self.zoom(t) * self.punch(t)
        world = self.bg.copy()
        # floor shadow
        person, ox, oy, ma = self.person(i, t)
        # big words behind / over him live in the world layer
        behind = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        if t < 1.62:
            p = spring(t, 10, 0.7)
            mw = txt("Money", "xb", 230, INK)
            place(behind, mw, W / 2, 840 + (1 - min(p, 1)) * 60, alpha=min(1, p * 2), scale=0.94 + 0.06 * min(p, 1.05), anchor="ct")
            if t >= 0.58:
                q = expo((t - 0.58) / 0.3)
                cb = txt("can" if t < 1.04 else "can buy", "md", 64, INK)
                place(behind, cb, W / 2, 770 + (1 - q) * 12, alpha=q, anchor="ct")
        world.alpha_composite(behind)
        world.alpha_composite(person, (int(ox), int(oy)))
        # camera: scale world about the head area
        if abs(z - 1) > 1e-3:
            cw, ch = int(W * z), int(H * z)
            ax, ay = W / 2, 1180
            zw = world.resize((cw, ch), Image.BICUBIC)
            canvas = self.bg.copy()
            canvas.alpha_composite(zw, (int(ax - ax * z), int(ay - ay * z))) if z < 1 else None
            if z >= 1:
                x0, y0 = int(ax * z - ax), int(ay * z - ay)
                canvas = zw.crop((x0, y0, x0 + W, y0 + H))
            world = canvas
        frame = world
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        self.overlay(ov, t)
        frame.alpha_composite(ov)
        out = np.asarray(frame.convert("RGB")).astype(np.float32) / 255
        # whip transitions on the shot changes
        for b in WHIP:
            d = t - b
            if -0.08 <= d < 0.12:
                k = 1 - abs(d) / (0.08 if d < 0 else 0.12)
                out = np.roll(cv2.blur(out, (int(1 + 120 * k) | 1, 1)), int(W * 0.3 * k * (-1 if d < 0 else 1)), axis=1)
        # inverted silhouette flashes
        if any(0 <= t - f0 < 2 / FPS + 1e-6 for f0 in FLASH):
            lum = out.mean(2)
            ink_bits = (lum < 0.55).astype(np.float32)
            graphic = np.asarray(ov.getchannel("A")).astype(np.float32) / 255 > 0.5
            sil = np.clip(ink_bits * (lum < 0.92) + graphic, 0, 1)
            sil = cv2.medianBlur((sil * 255).astype(np.uint8), 5).astype(np.float32) / 255
            out = np.dstack([sil] * 3) * np.array([1, 1, 1]) + (1 - sil[..., None]) * (np.array(INK) / 255)
        # gentle grain
        rng = np.random.default_rng(fi)
        out = out + rng.standard_normal(out.shape[:2]).astype(np.float32)[..., None] * 0.012
        return (np.clip(out, 0, 1) * 255).astype(np.uint8)

    # ---- overlay graphics ---------------------------------------------------------------
    def typed(self, ov, t, words, y=250, size=52):
        """Small sentence-case line, typed word by word, centred."""
        ims = [txt(w, "md", size, INK) for _, w in words]
        sp = int(size * 0.28)
        tw = sum(im.width for im in ims) + sp * (len(ims) - 1)
        x = (W - tw) / 2
        for (st, w), im in zip(words, ims):
            q = expo((t - st) / 0.25)
            if q > 0:
                place(ov, im, x, y + (1 - q) * 10, alpha=q * 0.95, blur=(1 - q) * 3)
            else:
                g = im.copy(); g.putalpha(g.getchannel("A").point(lambda v: int(v * 0.12)))
                ov.alpha_composite(g, (int(x), int(y)))
            x += im.width + sp

    def glow_word(self, ov, t, t0, s, y, size=250, kind="xb", grey=False):
        if t < t0:
            return
        p = spring(t - t0, 12, 0.6)
        top, bot = ((206, 206, 200), (120, 120, 112)) if grey else ((230, 255, 140), OLIVE)
        gw = glow(gradient_word(s, size, top, bot, kind), (G300 if grey else LIME), 26, 1.6 if not grey else 0.6)
        place(ov, gw, W / 2, y + (1 - min(p, 1)) * 70, alpha=min(1, p * 1.8), scale=0.86 + 0.14 * min(p, 1.06),
              blur=(1 - clamp01(p)) * 8, anchor="ct")
        # pixel glitch squares for half a second
        d = t - t0
        if d < 0.7 and not grey:
            rng = np.random.default_rng(int(t * FPS))
            dr = ImageDraw.Draw(ov)
            for _ in range(int(14 * (1 - d / 0.7))):
                x = W / 2 + rng.uniform(-420, 420); yy = y + rng.uniform(-40, size * 1.1)
                sz = rng.choice([10, 16, 24, 34])
                dr.rectangle((x, yy, x + sz, yy + sz), fill=LIME + (int(rng.uniform(120, 230)),))
        # sparkles
        for k, (sx, sy, ph) in enumerate(((-0.42, -0.05, 0.0), (-0.36, 0.08, 0.4), (0.44, 0.6, 0.8))):
            q = spring(t - t0 - 0.15 - k * 0.07, 14, 0.5)
            if q > 0.02:
                place(ov, sparkle(30 if k else 44), W / 2 + sx * W, y + sy * size * 2, scale=max(q, 0.01),
                      rot=(t - t0) * 90 + ph * 60, anchor="c")

    def fly(self, ov, im, t, t0, x, y, ry=0.0, rx=0.0, rz=0.0, from_y=-700, glow_c=None, exit_t=None, exit_dir=-1):
        """A card flies in from above with motion blur and settles with a gentle float."""
        if t < t0:
            return
        p = spring(t - t0, 9, 0.62)
        vel = abs(spring(t - t0 + 1 / FPS, 9, 0.62) - p) * abs(from_y) * FPS / 30
        ex = 0.0
        if exit_t is not None and t >= exit_t:
            ex = expo((t - exit_t) / 0.4)
            if ex >= 0.999:
                return
        fy = y + from_y * (1 - p) + exit_dir * 1400 * ex * ex + 10 * math.sin((t - t0) * 2.2)
        rot_y = ry * (0.4 + 0.6 * min(p, 1)) + 6 * math.sin((t - t0) * 1.3)
        card = persp(im, rot_y, rx + 20 * (1 - min(p, 1)), rz * min(p, 1))
        card = drop_shadow(card)
        if glow_c:
            card = glow(card, glow_c, 30, 0.55 * (1 - min(1, (t - t0) / 1.2)) + 0.18, p=50)
        card = vblur(card, vel * 0.8 + ex * 60)
        place(ov, card, x, fy, alpha=min(1, p * 2), scale=0.9 + 0.1 * min(p, 1.05), anchor="c")

    def arc(self, ov, t, t0, cx, cy, r):
        """A light arc whipping around a card."""
        d = t - t0
        if not (0 <= d < 0.7):
            return
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dr = ImageDraw.Draw(lay)
        a0 = -120 + 520 * expo(d / 0.7)
        for k in range(10):
            a = a0 - k * 9
            al = int(255 * (1 - k / 10) * (1 - d / 0.7))
            x = cx + r * math.cos(math.radians(a)); y = cy + r * 0.55 * math.sin(math.radians(a))
            dr.ellipse((x - 9, y - 9, x + 9, y + 9), fill=LIME + (al,))
        lay = glow(lay, LIME, 14, 1.4, p=0)
        ov.alpha_composite(lay)

    def overlay(self, ov, t):
        w = self.work
        # 1.3 - 3.04: "Happiness" card stack flies in on the pull-back
        if 1.30 <= t < 3.4:
            self.fly(ov, gloss_tile("dollar", 360), t, 1.30, W * 0.33, 560, ry=18, rz=-8, glow_c=LIME, exit_t=3.04)
            self.fly(ov, photo_card("car", "Happiness", "money can buy it?", w, 420, 550), t, 1.40, W * 0.64, 520, ry=-16, rz=6,
                     exit_t=3.04)
            self.arc(ov, t, 2.20, W * 0.52, 520, 330)
        if 1.82 <= t < 3.04:
            self.typed(ov, t, [(1.82, "and"), (2.04, "I'm"), (2.22, "gonna"), (2.26, "stand"), (2.58, "by"), (2.78, "that")], y=180)
        # 3.04 - 4.9: small line
        if 3.04 <= t < 4.22:
            self.typed(ov, t, [(3.04, "But"), (3.34, "I"), (3.44, "think"), (3.54, "most"), (3.88, "of"), (4.08, "us")], y=420)
        if 4.22 <= t < 5.12:
            self.typed(ov, t, [(4.22, "get"), (4.40, "a"), (4.52, "little"), (4.64, "bit"), (4.80, "of")], y=330)
            self.glow_word(ov, t, 4.90, "money", 420)
        # 5.12 - 6.44: "spend it on things" -> item cards fan in on the left, like a screen stack
        if 5.12 <= t < 6.6:
            self.typed(ov, t, [(5.12, "and"), (5.32, "then"), (5.42, "we"), (5.52, "spend"), (5.78, "it"), (5.92, "on"),
                               (6.06, "things")], y=330)
            for k, (st, kind, lab, pr) in enumerate(((5.52, "bag", "Bag", "$640"), (5.80, "watch", "Watch", "$720"),
                                                     (6.06, "shoe", "Sneakers", "$290"))):
                self.fly(ov, item_card(kind, lab, pr), t, st, 230 + k * 310, 640 + (k % 2) * 40, ry=(k - 1) * -14,
                         rz=(k - 1) * 5, from_y=500, exit_t=6.40)
        # 6.48 - 8.42: "that are the worst at buying / Happiness"
        if 6.48 <= t < 8.77:
            self.typed(ov, t, [(6.48, "that"), (6.58, "are"), (6.72, "the"), (6.72, "worst"), (7.10, "at"), (7.34, "buying")], y=330)
            self.glow_word(ov, t, 7.82, "Happiness", 420, size=210)
        # 8.77 - 10.54: "you make a little bit more money and so you upgrade": bank card
        if 8.77 <= t < 10.6:
            self.typed(ov, t, [(8.92, "make"), (9.06, "a"), (9.18, "little"), (9.32, "bit"), (9.46, "more"), (9.64, "money")]
                       if t < 9.86 else [(9.86, "and"), (10.00, "so"), (10.14, "you")], y=250)
            self.fly(ov, gloss_tile("card", 300), t, 9.0, W / 2, 560, ry=-20, rx=12, rz=-6, glow_c=LIME, exit_t=10.48)
            if t >= 9.25:
                q = spring(t - 9.25, 14, 0.6)
                badge = txt("+ $3,600", "xb", 64, INK)
                bp = Image.new("RGBA", (badge.width + 56, 96), (0, 0, 0, 0))
                ImageDraw.Draw(bp).rounded_rectangle((0, 0, bp.width - 1, 95), 48, fill=LIME + (255,))
                bp.alpha_composite(badge, (28, (96 - badge.height) // 2))
                place(ov, drop_shadow(bp, 16, 0.2, 12), W * 0.68, 790, scale=max(q, 0.01), alpha=1 - smooth((t - 10.4) / 0.1),
                      anchor="c")
            self.glow_word(ov, t, 10.24, "upgrade", 330, size=200)
        # 10.54 - 12.24: the car, the house, the vacation -> photo cards stack in
        if 10.54 <= t < 14.6:
            cards = ((10.54, "car", "The car", "upgraded"), (11.08, "house", "The house", "upgraded"),
                     (11.62, "jetski", "The vacation", "upgraded"))
            for k, (st, key, title, sub) in enumerate(cards):
                x = W / 2 + (k - 1) * 230
                y = 610 + abs(k - 1) * 30
                self.fly(ov, photo_card(key, title, sub, w), t, st, x, y, ry=(k - 1) * -18, rz=(k - 1) * 7,
                         glow_c=LIME, exit_t=14.30)
            self.arc(ov, t, 11.62, W / 2, 600, 420)
        # 12.24 - 14.42: "Eventually that life just feels normal"
        if 12.24 <= t < 14.42:
            self.typed(ov, t, [(12.24, "Eventually"), (12.76, "that"), (13.08, "life"), (13.36, "just"), (13.62, "feels")], y=90)
            self.glow_word(ov, t, 13.92, "normal.", 165, size=150, kind="serif", grey=True)
        # 14.42 - end
        if 14.42 <= t < 15.98:
            self.typed(ov, t, [(14.42, "and"), (14.70, "so"), (14.86, "you"), (15.02, "no"), (15.22, "longer"), (15.44, "have"),
                               (15.78, "that")], y=420)
        if t >= 15.98:
            self.typed(ov, t, [(16.46, "that"), (16.76, "can"), (16.92, "come"), (17.12, "from"), (17.30, "it")], y=330)
            self.glow_word(ov, t, 15.98, "happiness", 420, size=200)


SFX = ([(t, "whoosh") for t in (1.30, 3.13, 5.52, 8.77, 9.0, 10.54, 11.08, 11.62, 14.3)]
       + [(t, "thock") for t in (1.36, 4.90, 7.82, 10.24, 15.98)]
       + [(t, "bloop") for t in (5.80, 6.06, 9.25)]
       + [(t, "flash") for t in FLASH]
       + [(t, "air") for t in (2.20, 13.92)])
b1.SFX[:] = SFX

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
            Image.fromarray(R.frame(fi)).save(os.path.join(work, f"sf_{fi:04d}.png"))
        return
    vid = os.path.join(work, "video_saas_full.mp4")
    p = subprocess.Popen(f'ffmpeg -v error -y -f rawvideo -pix_fmt rgb24 -s {W}x{H} -r {FPS} -i - '
                         f'-c:v libx264 -preset slow -crf 15 -pix_fmt yuv420p "{vid}"', shell=True, stdin=subprocess.PIPE)
    with Pool(3, initializer=_init, initargs=(work,)) as pool:
        for buf in pool.imap(_frame, range(N), chunksize=3):
            p.stdin.write(buf)
    p.stdin.close(); p.wait()
    mix, master = os.path.join(work, "mix_sf.wav"), os.path.join(work, "master_sf.wav")
    b1.build_audio(work, mix, music, start)
    v1.loudnorm(mix, master)
    out = os.path.join(work, "AVE_Braiden_SaaS.mp4")
    v1.sh(f'ffmpeg -v error -y -i "{vid}" -i "{master}" -c:v copy -c:a aac -b:a 256k -shortest -movflags +faststart "{out}"')
    print(out)


if __name__ == "__main__":
    cmd, src, work = sys.argv[1:4]
    if cmd == "render":
        render(work, sys.argv[4] if len(sys.argv) > 4 else None, float(sys.argv[5]) if len(sys.argv) > 5 else 0.0)
    elif cmd == "stills":
        render(work, only=[int(round(float(x) * FPS)) for x in sys.argv[4:]])
