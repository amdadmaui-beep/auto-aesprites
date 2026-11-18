"""Braiden re-edit V3: the "go all out" pass.

On top of V2's layout and graphics:
  * captions for every spoken line (bold sans + teal serif keyword, word pops);
  * punch-in zooms with decaying shake on key words, subtle handheld drift;
  * zoom-blur, whip-pan (motion blur + colour fringing) and light-leak transitions;
  * 2.5D cut-aways: subject cut out of each still and moved against an
    inpainted background (car/house parallax, the jet ski drives forward,
    water shimmer, sun flare);
  * film finish: grain, highlight halation, slight lens fringing, vignette;
  * restrained glow so graphics read as designed, not generated.

Needs everything build_v2.py needs, plus WORK/broll/{car,house,jetski}_m.png
(isnet-general-use masks of the stills, 1600x900).

Usage: python build_v3.py render SOURCE.mp4 WORK [MUSIC.mp3 START]
       python build_v3.py stills SOURCE.mp4 WORK 1.0 ...
"""
import math, os, subprocess, sys
from functools import lru_cache

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
import importlib.util  # noqa: E402
_spec = importlib.util.spec_from_file_location("braiden_v2", os.path.join(HERE, "build_v2.py"))
b2 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(b2)
from build_v3 import expo, spring, smooth, clamp01, place  # noqa: E402  (before-after-reel helpers)

b1, v1 = b2.b1, b2.v1
W, H, FPS, PW, PH = b2.W, b2.H, b2.FPS, b2.PW, b2.PH
N, END = b2.N, b2.END
TEAL, TEAL_D, TEAL_L, WHITE = b2.TEAL, b2.TEAL_D, b2.TEAL_L, b2.WHITE
BOX_FG = BAND_FG = WHITE   # text on the accent box / band (a palette can override)
word, pad, banknote, coin, engraving, dot_grid = b2.word, b2.pad, b2.banknote, b2.coin, b2.engraving, b2.dot_grid

CUTS = [(10.54, 11.08, "car"), (11.08, 11.62, "house"), (11.62, 14.45, "jetski")]
PUNCH = [(0.0, 0.0), (1.30, 0.035), (4.90, 0.07), (6.72, 0.06), (7.82, 0.04), (10.24, 0.08), (15.98, 0.06)]
WHIPS = [8.77, 10.54, 11.08, 11.62]        # whip-pan transitions
ZOOMS = [0.50, 3.13, 14.45]               # zoom-blur transitions
LEAKS = [(0.50, 0.7), (3.13, 0.6), (10.54, 0.5), (14.45, 0.9), (15.98, 0.5)]

# caption groups: (start, end, [(time, word, keyword?)])
def _g(start, end, words):
    return (start, end, [(t, w.lstrip("*"), w.startswith("*")) for t, w in words])


CAPS = [
    _g(1.82, 3.04, [(1.82, "and"), (2.04, "I'm"), (2.22, "gonna"), (2.26, "*stand"), (2.58, "by"), (2.78, "that")]),
    _g(3.04, 4.22, [(3.04, "But"), (3.34, "I"), (3.44, "think"), (3.54, "most"), (3.88, "of"), (4.08, "us")]),
    _g(4.22, 5.12, [(4.22, "get"), (4.40, "a"), (4.52, "little"), (4.64, "bit"), (4.80, "of"), (4.90, "*money")]),
    _g(5.12, 6.44, [(5.12, "and"), (5.32, "then"), (5.42, "we"), (5.52, "*spend"), (5.78, "it"), (5.92, "on"), (6.06, "things")]),
    _g(8.42, 9.86, [(8.42, "you"), (8.92, "make"), (9.06, "a"), (9.18, "little"), (9.32, "bit"), (9.46, "more"), (9.64, "*money")]),
    _g(9.86, 10.54, [(9.86, "and"), (10.00, "so"), (10.14, "you"), (10.24, "*upgrade")]),
    _g(10.54, 11.08, [(10.54, "the"), (10.72, "*car")]),
    _g(11.08, 11.62, [(11.08, "the"), (11.28, "*house")]),
    _g(11.62, 12.24, [(11.62, "or"), (11.76, "the"), (11.84, "*vacation")]),
    _g(12.24, 13.62, [(12.24, "*Eventually"), (12.76, "that"), (13.08, "life"), (13.36, "just")]),
    _g(13.62, 14.42, [(13.62, "feels"), (13.92, "*normal")]),
    _g(14.42, 15.44, [(14.42, "and"), (14.70, "so"), (14.86, "you"), (15.02, "no"), (15.22, "longer")]),
    _g(15.44, END + 1, [(15.44, "Have"), (15.78, "that"), (15.98, "*happiness"), (16.46, "|that"), (16.76, "can"),
                        (16.92, "come"), (17.12, "from"), (17.30, "it")]),
]

SFX = ([(t, "whoosh") for t in WHIPS + ZOOMS]
       + [(t, "thock") for t, a in PUNCH if a >= 0.05]
       + [(1.30, "flash"), (4.90, "ding"), (6.40, "air"), (13.92, "air"), (15.98, "bloop")])


# ===========================================================================
def radial_blur(a, amount, cx=0.5, cy=0.45, n=7):
    if amount < 0.003:
        return a
    h, w = a.shape[:2]
    acc = np.zeros_like(a)
    for k in range(n):
        s = 1 + amount * k / (n - 1)
        M = cv2.getRotationMatrix2D((cx * w, cy * h), 0, s)
        acc += cv2.warpAffine(a, M, (w, h), borderMode=cv2.BORDER_REFLECT)
    return acc / n


def h_blur(a, px):
    px = int(px) | 1
    return a if px <= 1 else cv2.blur(a, (px, 1))


def fringe(a, amt):
    """Lens colour fringing: scale R up and B down around the centre."""
    if amt < 1e-4:
        return a
    h, w = a.shape[:2]
    out = a.copy()
    for ch, s in ((0, 1 + amt), (2, 1 - amt)):
        M = cv2.getRotationMatrix2D((w / 2, h / 2), 0, s)
        out[..., ch] = cv2.warpAffine(a[..., ch], M, (w, h), borderMode=cv2.BORDER_REFLECT)
    return out


class Renderer(b2.Renderer):
    def __init__(self, work):
        super().__init__(work)
        rng = np.random.default_rng(11)
        self.grain = [cv2.GaussianBlur(rng.standard_normal((PH, PW)).astype(np.float32), (0, 0), 0.7) for _ in range(6)]
        yy, xx = np.mgrid[0:PH, 0:PW].astype(np.float32)
        self.yy, self.xx = yy, xx
        self.layers = {k: self.make_layers(k) for k in ("car", "house", "jetski")}

    # ---- 2.5D layers for the stills ----------------------------------------------
    def make_layers(self, key):
        im = np.asarray(self.broll[key].resize((1600, 900), Image.LANCZOS)).astype(np.float32) / 255
        m = np.asarray(Image.open(os.path.join(self.work, "broll", key + "_m.png")).convert("L")).astype(np.float32) / 255
        if key == "jetski":
            m = np.clip((m - 0.55) / 0.3, 0, 1)
        hard = (m > 0.35).astype(np.uint8)
        hole = cv2.dilate(hard, np.ones((25, 25), np.uint8))
        bg = cv2.inpaint((im * 255).astype(np.uint8), hole, 9, cv2.INPAINT_TELEA).astype(np.float32) / 255
        m = cv2.GaussianBlur(m, (0, 0), 1.2)
        return im, bg, m

    def cutaway(self, key, dt, dur):
        im, bg, m = self.layers[key]
        h, w = bg.shape[:2]
        p = dt / dur

        def warp(a, s, cx, cy, dx=0, dy=0):
            M = cv2.getRotationMatrix2D((cx, cy), 0, s); M[0, 2] += dx; M[1, 2] += dy
            return cv2.warpAffine(a, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

        if key == "car":
            cx, cy = 0.62 * w, 0.78 * h
            B = warp(bg, 1.05 + 0.03 * p, cx, cy, -20 * p)
            F = warp(im, 1.05 + 0.11 * p, cx, cy, -45 * p); M_ = warp(m, 1.05 + 0.11 * p, cx, cy, -45 * p)
        elif key == "house":
            cx, cy = 0.5 * w, 0.62 * h
            B = warp(bg, 1.0 + 0.03 * p, cx, cy, 0, -10 * p)
            F = warp(im, 1.0 + 0.09 * p, cx, cy, 0, -6 * p); M_ = warp(m, 1.0 + 0.09 * p, cx, cy, 0, -6 * p)
        else:
            # water shimmer below the horizon, the jet ski drives forward along its wake
            yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
            water = (yy > 0.36 * h).astype(np.float32)
            mx = xx + water * (2.0 * np.sin(yy / 9 + dt * 7) + 1.2 * np.sin(xx / 23 + dt * 4))
            my = yy + water * (1.4 * np.sin(xx / 13 + dt * 6))
            B = cv2.remap(bg, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            Bw = cv2.remap(im, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            wake = np.clip(np.asarray(Image.open(os.path.join(self.work, "broll", "jetski_m.png")).convert("L"),
                                      np.float32) / 255 * 1.6, 0, 1)[..., None]
            wake = wake * (1 - cv2.dilate((m > 0.2).astype(np.uint8), np.ones((31, 31), np.uint8))[..., None])
            B = B * (1 - wake) + Bw * wake          # keep the wake (not the jet ski) on the water layer
            sx, sy = 120 * p, -32 * p + 3 * math.sin(dt * 9)
            F = warp(im, 1.0, 0, 0, sx, sy); M_ = warp(m, 1.0, 0, 0, sx, sy)
        a = B * (1 - M_[..., None]) + F * M_[..., None]
        # camera on top
        if key == "jetski":
            k, ccx, ccy = 1.28 + 0.05 * p, 0.62 + 0.08 * p, 0.6
        else:
            k, ccx, ccy = 1.0, 0.5, 0.5
        cw, ch = w / k, h / k
        x0 = min(max(ccx * w - cw / 2, 0), w - cw); y0 = min(max(ccy * h - ch / 2, 0), h - ch)
        a = cv2.resize(a[int(y0):int(y0 + ch), int(x0):int(x0 + cw)], (PW, PH), interpolation=cv2.INTER_AREA)
        if key == "car":   # sun flare breathing
            sx_, sy_ = PW * 0.30, PH * 0.44
            d2 = ((self.xx - sx_) ** 2 + (self.yy - sy_) ** 2)
            fl = np.exp(-d2 / (2 * 70 ** 2)) * (0.35 + 0.1 * math.sin(dt * 8)) + \
                np.exp(-((self.xx - sx_) / 420) ** 2 - ((self.yy - sy_) / 6) ** 2) * 0.25
            a = a + fl[..., None] * np.array([1.0, 0.75, 0.45])
        return np.clip(a, 0, 1)

    # ---- camera -----------------------------------------------------------------
    def cam(self, t):
        if t < 0.5:
            k = 1.75 - 0.25 * smooth(t / 0.5); cx, cy = 0.40, 0.30
        elif t < 3.13:
            k = 1.0 + 0.05 * smooth((t - 0.5) / 2.6); cx, cy = 0.45, 0.4
        elif t < 8.77:
            k = 1.04 + 0.05 * smooth((t - 3.13) / 5.6); cx, cy = 0.4, 0.4
        elif t < 14.45:
            k = 1.02 + 0.05 * smooth((t - 8.77) / 1.8); cx, cy = 0.5, 0.45
        elif t < 15.0:
            k = 1.9 - 0.85 * expo((t - 14.45) / 0.55); cx, cy = 0.5, 0.35
        else:
            k = 1.05 + 0.04 * smooth((t - 15.0) / 2.6); cx, cy = 0.5, 0.45
        dx = dy = 0.0
        for t0, amt in PUNCH:
            d = t - t0
            if amt and 0 <= d < 1.2:
                k += amt * expo(d / 0.12) * (1 - 0.7 * smooth((d - 0.15) / 0.9))
                e = math.exp(-d * 9) * amt * 160
                dx += e * math.sin(d * 63); dy += e * math.cos(d * 51)
        # gentle handheld drift
        dx += 2.2 * math.sin(t * 1.3) + 1.2 * math.sin(t * 2.9)
        dy += 1.6 * math.sin(t * 1.7 + 1)
        cw, ch = PW / k, PH / k
        x0 = min(max(cx * PW - cw * cx + dx, 0), PW - cw); y0 = min(max(cy * PH - ch * cy + dy, 0), PH - ch)
        return (x0, y0, x0 + cw, y0 + ch)

    def box(self, t):
        return self.cam(t)

    # ---- speaker shots: V2 graphics, refined -------------------------------------
    def speaker(self, i, t):
        bx = self.cam(t)
        src = np.asarray(self.raw(i).resize((PW, PH), Image.BICUBIC, box=bx)).astype(np.float32) / 255
        m = np.asarray(Image.fromarray((self.mask(i) * 255).astype(np.uint8)).resize((PW, PH), Image.BILINEAR, box=bx)).astype(np.float32) / 255
        m = cv2.GaussianBlur(m, (0, 0), 1.0)
        img = self.grade(src)
        if 13.6 <= t < 15.0 or 12.24 <= t < 14.45:
            pass
        bgl = Image.new("RGBA", (PW, PH), (0, 0, 0, 0))
        fg = Image.new("RGBA", (PW, PH), (0, 0, 0, 0))
        teal = np.array(TEAL_L, np.float32) / 255
        if t < 0.5:
            g = dot_grid() * 0.5 * (1 - m)
            img = img * (1 - g[..., None] * 0.45) + teal * g[..., None] * 0.45
            n = b2.glow(pad(banknote(260, 118), 30), 14, 0.45)
            place(bgl, n.rotate(-8 + t * 10, resample=Image.BICUBIC, expand=True), 250, 210 - t * 20, anchor="c")
            mc = word("Money can buy", "urb700", 64, WHITE)
            place(fg, self.shadowed(mc), -mc.width + (mc.width + 30) * expo(t / 0.5) - 10, 70)
        elif t < 3.13:
            p = expo((t - 0.5) / 0.6)
            ang = -(t - 0.5) * 22
            wh = self.wheel_blur(ang)
            place(bgl, wh, PW * 0.60, PH * 0.27, scale=0.7 + 0.3 * p, alpha=p, anchor="c")
            pm = expo((t - 0.5) / 0.4)
            place(fg, self.shadowed(word("Money can buy", "urb600", 46, WHITE)), 50 + (1 - pm) * -60, 142, alpha=pm)
            if t >= 1.30:
                q = expo((t - 1.30) / 0.45)
                d = ImageDraw.Draw(fg)
                hp = word("Happiness", "serif800", 86, BOX_FG)
                d.rectangle((0, 226, int((hp.width + 70) * q), 226 + 98), fill=TEAL + (240,))
                # letters rise in one by one
                x = 34
                for li, ch in enumerate("Happiness"):
                    lw_ = word(ch, "serif800", 86, BOX_FG)
                    lq = expo((t - 1.36 - li * 0.035) / 0.35)
                    if lq > 0:
                        place(fg, lw_, x, 224 + (1 - lq) * 40, alpha=lq, blur=(1 - lq) * 4)
                    x += b2.font("serif800", 86).getlength(ch)
        elif t < 6.44:
            e = engraving()
            p = smooth((t - 3.13) / 0.5)
            drift = np.roll(e, int((t - 3.13) * 6), axis=1)
            img = img * (1 - drift[..., None] * 0.5 * p * (1 - m[..., None])) + teal * drift[..., None] * 0.45 * p * (1 - m[..., None])
            if t >= 4.90:
                q = spring(t - 4.90, 12, 0.6)
                place(bgl, coin(t), PW * 0.80, PH * 0.32, scale=max(q, 0.01), anchor="c")
        elif t < 8.77:
            e = engraving()
            img = img * (1 - e[..., None] * 0.5 * (1 - m[..., None])) + teal * e[..., None] * 0.28 * (1 - m[..., None])
            p = expo((t - 6.40) / 0.45)
            bh = int(PH * 0.45)
            band = Image.new("RGBA", (PW, PH), (0, 0, 0, 0))
            db = ImageDraw.Draw(band)
            db.rectangle((0, 0, PW, int(bh * p)), fill=TEAL + (255,))
            # subtle diagonal sheen moving across the band
            sx = (t - 6.4) * 700 - 200
            bgl.alpha_composite(band)
            sheen = Image.new("RGBA", (PW, PH), (0, 0, 0, 0))
            ImageDraw.Draw(sheen).polygon([(sx, 0), (sx + 90, 0), (sx - 60, bh * p), (sx - 150, bh * p)], fill=(255, 255, 255, 40))
            bgl.alpha_composite(sheen)
            x = PW * 0.47
            for st, wd in ((6.48, "are"), (6.58, "the"), (6.72, "worst"), (7.10, "at"), (7.34, "buying")):
                w_ = word(wd, "urb600" if wd != "worst" else "urb800", 48, BAND_FG)
                q = expo((t - st) / 0.3)
                if q > 0:
                    place(fg, w_, x, 92 + (1 - q) * 14, alpha=q, blur=(1 - q) * 4)
                x += w_.width + 12
            if t >= 7.82:
                q = expo((t - 7.82) / 0.45)
                hp = word("Happiness", "serif800", 92, WHITE)
                bx0 = PW * 0.47 - 30
                ImageDraw.Draw(fg).rectangle((bx0, 160, bx0 + (hp.width + 60) * q, 270), fill=TEAL_D + (255,))
                place(fg, hp, bx0 + 30 + (1 - q) * 40, 160, alpha=q)
        # "normal": colour drains, then returns on "happiness"
        if 13.3 <= t < 16.4:
            s = 1 - 0.85 * smooth((t - 13.6) / 0.8) + 0.85 * smooth((t - 15.9) / 0.5)
            lum = img.mean(2, keepdims=True); img = lum + (img - lum) * s
        bga = np.asarray(bgl).astype(np.float32) / 255
        if bga[..., 3].any():
            al = bga[..., 3:4] * (1 - m[..., None])
            img = img * (1 - al) + bga[..., :3] * al
        out = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)).convert("RGBA")
        if 6.40 <= t < 8.77:
            mm = (m > 0.5).astype(np.uint8)
            ring = cv2.dilate(mm, np.ones((7, 7), np.uint8)) - mm
            ring[int(PH * 0.45 * expo((t - 6.40) / 0.45)):] = 0
            rl = Image.new("RGBA", (PW, PH), WHITE + (0,))
            rl.putalpha(Image.fromarray((cv2.GaussianBlur(ring.astype(np.float32), (0, 0), 0.8) * 255).astype(np.uint8)))
            out.alpha_composite(rl)
        out.alpha_composite(fg)
        return np.asarray(out.convert("RGB")).astype(np.float32) / 255

    @lru_cache(None)
    def wheel_base(self):
        w = Image.new("RGBA", b2.money_wheel().size, (0, 0, 0, 0))
        # rebuild with a softer glow than V2
        size = w.width
        note = banknote(170, 76)
        c = size / 2
        for k in range(26):
            ang = k * (360 / 26)
            n = note.rotate(-ang, resample=Image.BICUBIC, expand=True)
            a = math.radians(ang)
            w.alpha_composite(n, (int(c + 120 * math.cos(a) - n.width / 2), int(c + 120 * math.sin(a) - n.height / 2)))
        return b2.glow(w, 16, 0.35)

    def wheel_blur(self, ang):
        base = self.wheel_base()
        acc = None
        for k in range(3):   # rotational motion blur
            r = np.asarray(base.rotate(ang + k * 1.4, resample=Image.BICUBIC)).astype(np.float32)
            acc = r if acc is None else acc + r
        return Image.fromarray((acc / 3).astype(np.uint8))

    @staticmethod
    def shadowed(im, r=8, a=0.55):
        p = pad(im, 20)
        sh = Image.new("RGBA", p.size, (0, 0, 0, 0))
        sh.putalpha(p.getchannel("A").filter(ImageFilter.GaussianBlur(r)).point(lambda v: int(v * a)))
        out = Image.new("RGBA", p.size, (0, 0, 0, 0)); out.alpha_composite(sh, (0, 4)); out.alpha_composite(p)
        return out

    # ---- captions -----------------------------------------------------------------
    @lru_cache(None)
    def cap_word(self, w, key):
        if key:
            return self.shadowed(word(w, "serif800", 60, TEAL_L), 12, 0.9)
        return self.shadowed(word(w, "urb800", 50, WHITE), 12, 0.8)

    def captions(self, base, t):
        for st, en, words in CAPS:
            if not (st - 0.05 <= t < en):
                continue
            ex = smooth((en - t) / 0.12) if en < END else 1.0
            lines, cur = [], []
            for tw, w, k in words:
                if w.startswith("|"):
                    lines.append(cur); cur = []; w = w[1:]
                cur.append((tw, w, k))
            lines.append(cur)
            n = len(lines)
            for li, line in enumerate(lines):
                ims = [self.cap_word(w, k) for _, w, k in line]
                tw_ = sum(im.width - 40 for im in ims) + 14 * (len(ims) - 1)
                x = (PW - tw_) / 2
                y = PH - 70 - (n - li) * 62
                for (st_w, w, k), im in zip(line, ims):
                    q = spring(t - st_w + 0.04, 16, 0.65)
                    if q > 0.01:
                        sc = 1.18 - 0.18 * min(q, 1.2)
                        place(base, im, x - 20 + (im.width / 2) * (1 - sc), y - 20 + (1 - min(q, 1)) * 18 - (8 if k else 0)
                              - (1 - ex) * 14, alpha=min(1, q * 1.6) * ex, scale=sc, blur=(1 - clamp01(q)) * 3)
                    x += im.width - 40 + 14

    # ---- film finish + transitions --------------------------------------------------
    def leak(self, t):
        v = 0.0
        for t0, amt in LEAKS:
            d = t - t0
            if -0.15 <= d < 0.6:
                v = max(v, amt * (smooth((d + 0.15) / 0.15) if d < 0 else 1 - smooth(d / 0.6)))
        if v <= 0.01:
            return None
        cx = PW * (0.2 + 0.6 * (0.5 + 0.5 * math.sin(t * 2.3)))
        g1 = np.exp(-(((self.xx - cx) / 380) ** 2 + ((self.yy - PH * 0.3) / 260) ** 2))
        g2 = np.exp(-(((self.xx - (PW - cx)) / 300) ** 2 + ((self.yy - PH * 0.8) / 220) ** 2))
        return (g1[..., None] * np.array([1.0, 0.62, 0.32]) + g2[..., None] * np.array([0.25, 0.75, 0.8])) * v

    def frame_edit(self, i, t):
        cut = next((c for c in CUTS if c[0] <= t < c[1]), None)
        a = self.cutaway(cut[2], t - cut[0], cut[1] - cut[0]) if cut else self.speaker(i, t)
        # transitions
        for b in ZOOMS:
            d = t - b
            if -0.12 <= d < 0.16:
                k = 1 - abs(d) / (0.12 if d < 0 else 0.16)
                a = radial_blur(a, 0.18 * k)
        for b in WHIPS:
            d = t - b
            if -0.1 <= d < 0.12:
                k = 1 - abs(d) / (0.1 if d < 0 else 0.12)
                shift = int((PW * 0.22) * k * (-1 if d < 0 else 1))
                a = np.roll(h_blur(a, 90 * k), shift, axis=1)
                a = fringe(a, 0.012 * k)
        lk = self.leak(t)
        if lk is not None:
            a = 1 - (1 - a) * (1 - np.clip(lk, 0, 1))      # screen
        # captions sit on top of transitions so the words stay readable
        img = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).convert("RGBA")
        self.captions(img, t)
        a = np.asarray(img.convert("RGB")).astype(np.float32) / 255
        # finish: halation, lens fringe, grain, vignette
        lum = a.mean(2)
        hi = cv2.GaussianBlur(np.clip((lum - 0.72) / 0.28, 0, 1), (0, 0), 14)
        a = a + hi[..., None] * np.array([0.22, 0.10, 0.05])
        a = fringe(a, 0.0025)
        g = self.grain[int(t * FPS) % len(self.grain)]
        a = a + g[..., None] * (0.022 + 0.02 * (1 - lum[..., None]))
        a = a * self.vig
        return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).convert("RGBA")

    def frame(self, fi):
        t = fi / FPS
        i = fi + 1
        page = Image.new("RGB", (W, H), (0, 0, 0))
        page.paste(self.raw(i).resize((PW, PH + 1), Image.LANCZOS), (0, b2.RAW_Y))
        page.paste(self.frame_edit(i, t).convert("RGB"), (0, b2.EDIT_Y))
        return np.asarray(page)


R = None


def _init(work):
    global R
    b2.WORK = work
    R = Renderer(work)


def _frame(fi):
    return R.frame(fi).tobytes()


def render(work, music=None, start=0.0, only=None):
    from multiprocessing import Pool
    if only is not None:
        _init(work)
        for fi in only:
            Image.fromarray(R.frame(fi)).save(os.path.join(work, f"v3_{fi:04d}.png"))
        return
    vid = os.path.join(work, "video_v3.mp4")
    p = subprocess.Popen(f'ffmpeg -v error -y -f rawvideo -pix_fmt rgb24 -s {W}x{H} -r {FPS} -i - '
                         f'-c:v libx264 -preset slow -crf 14 -pix_fmt yuv420p "{vid}"', shell=True, stdin=subprocess.PIPE)
    with Pool(3, initializer=_init, initargs=(work,)) as pool:
        for buf in pool.imap(_frame, range(N), chunksize=3):
            p.stdin.write(buf)
    p.stdin.close(); p.wait()
    b1.SFX[:] = SFX
    mix, master = os.path.join(work, "mix_v3.wav"), os.path.join(work, "master_v3.wav")
    b1.build_audio(work, mix, music, start)
    v1.loudnorm(mix, master)
    out = os.path.join(work, "AVE_Braiden_Reedit_V3.mp4")
    v1.sh(f'ffmpeg -v error -y -i "{vid}" -i "{master}" -c:v copy -c:a aac -b:a 256k -shortest -movflags +faststart "{out}"')
    print(out)


if __name__ == "__main__":
    cmd, src, work = sys.argv[1:4]
    if cmd == "render":
        render(work, sys.argv[4] if len(sys.argv) > 4 else None, float(sys.argv[5]) if len(sys.argv) > 5 else 0.0)
    elif cmd == "stills":
        render(work, only=[int(round(float(x) * FPS)) for x in sys.argv[4:]])
