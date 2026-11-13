"""AVE Studio · Before / After reel, V3 (premium pass).

Changes from V2:
  * the speaker is in colour (color_from_ref.py: our clean footage carrying the
    reference's colour grade, without its text and graphics);
  * no emoji / sticker icons anywhere;
  * frosted-glass checklist pills, clean effect rows with animated toggles,
    a mood-board inspiration card and refined number cards;
  * smoother motion: expo / spring easing, blur-in, word-by-word captions,
    exits, and zoom-blur transitions between cards;
  * background music (user-supplied track) from its 0:24 drop, ducked under the voice.

Usage:
    python build_v2.py prep REF.mp4 WORK          # footage, cut-outs, voice, transcript
    python color_from_ref.py REF.mp4 WORK         # colour
    python build_v3.py render REF.mp4 WORK MUSIC.mp3 [MUSIC_START=24.0]
    python build_v3.py stills REF.mp4 WORK 1.0 7.5 ...
"""
import math, os, subprocess, sys
from functools import lru_cache

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import build as v1
import build_v2 as v2
from build import rounded_mask, fit, sh
from build_v2 import (txt, vgrad, hgrad, long_shadow, font, CARD, BEFORE, RADIUS, SRC_W, SRC_H, SRC_X, SRC_Y,
                      INK, PAPER, WHITE, LIME, LIMEt, LIME_PALE, LIME_DEEP, GREY, END, FPS, W, H)

SEGMENTS = v1.SEGMENTS
BOUNDS = [s[0] for s in SEGMENTS[1:]]
TR = 0.20   # half-length of a card transition (s)

NUM_CARDS = {1: (6.10, ("lack of", 6.62), ("DIRECTION", 7.00)),
             2: (20.58, ("bad", 21.12), ("DESIGN", 21.36)),
             3: (31.14, ("poor", 31.72), ("POST-PRODUCTION", 31.94))}
BIG = [  # (on, off, lines, kicker, kicker align)
    (0.62, 2.76, ["EDITS"], "IF YOU LOOK AT YOUR", "c"),
    (3.50, 5.87, ["INSTAGRAM"], "WHAT I SEE ON", "l"),
    (8.96, 11.50, ["YOU NEED TO KNOW", "EXACTLY"], None, "c"),
    (17.90, 20.47, ["YOU GONNA", "GET LOST"], None, "c"),
    (22.14, 24.87, ["DESIGN"], None, "c"),
    (29.24, 30.47, ["BEGINNER"], "YOU ARE A", "c"),
    (33.02, 35.42, ["PRODUCTION"], "POST", "c"),
    (35.52, 36.90, ["NEED TO LOOK"], "YOU", "c"),
    (41.94, END, ["REMEMBER"], "JUST MAKE SURE TO", "c"),
]
KICK_ONLY = [(0.0, 0.62, "IF YOU LOOK AT YOUR", "c"), (2.76, 3.50, "WHAT I SEE ON", "l"),
             (41.20, 41.94, "JUST MAKE SURE TO", "c")]
CAPS = v2.CAPS
CHECKS = v2.CHECKS
CHECKS_OFF = v2.CHECKS_OFF
BUBBLES = [(5.36, 5.87), (42.50, 44.00)]
FX_ROWS = [(37.06, "Vignette"), (37.76, "Blur"), (38.46, "Chromatic aberration"),
           (39.62, "Noise"), (40.30, "Posterize time")]
INSP = dict(vault=12.20, house=13.70, more=14.22, refs=14.80)

SFX = ([(t, "whoosh") for t in BOUNDS]
       + [(t, "thock") for t in (6.10, 20.58, 31.14)]
       + [(t, "flash") for t in (0.62, 3.50, 8.96, 17.90, 29.24, 35.52, 41.94)]
       + [(t, "bloop") for t in (5.36, 25.26, 26.46, 27.26, 42.50, 12.20)]
       + [(14.22, "air")]
       + [(t + 0.22, "ding") for t, _ in FX_ROWS])


# ---- easing ---------------------------------------------------------------
def clamp01(x):
    return min(max(x, 0.0), 1.0)


def expo(p):
    p = clamp01(p)
    return 1.0 if p >= 1 else 1 - 2 ** (-10 * p)


def smooth(p):
    p = clamp01(p)
    return p * p * (3 - 2 * p)


def spring(t, w=15.0, z=0.62):
    """Damped spring from 0 to 1, t in seconds since start."""
    if t <= 0:
        return 0.0
    wd = w * math.sqrt(1 - z * z)
    return 1 - math.exp(-z * w * t) * (math.cos(wd * t) + z * w / wd * math.sin(wd * t))


def exit_k(t, off, dur=0.2):
    """1 while held, easing to 0 over `dur` before `off` (no exit if off is a cut)."""
    if any(abs(off - b) < 0.02 for b in BOUNDS) or off >= END - 0.01:
        return 1.0
    return smooth((off - t) / dur)


def place(base, im, x, y, alpha=1.0, scale=1.0, blur=0.0, anchor="lt", rot=0.0):
    if alpha <= 0.004 or scale <= 0.01:
        return
    if blur > 0.4:
        pad = int(blur * 2.5) + 2
        im2 = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
        im2.alpha_composite(im, (pad, pad))
        im = im2.filter(ImageFilter.GaussianBlur(blur))
        x -= pad * (1 if anchor == "lt" else 0); y -= pad * (1 if anchor in ("lt", "ct") else 0)
    if rot:
        im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    if abs(scale - 1) > 1e-3:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BICUBIC)
    if alpha < 0.999:
        a = np.asarray(im.getchannel("A")).astype(np.float32) * alpha
        im = im.copy(); im.putalpha(Image.fromarray(a.astype(np.uint8)))
    if anchor == "c":
        x, y = x - im.width / 2, y - im.height / 2
    elif anchor == "ct":
        x = x - im.width / 2
    base.alpha_composite(im, (int(round(x)), int(round(y))))


def tracked(s, kind, size, color, track):
    f = font(kind, size)
    ws = [f.getlength(c) for c in s]
    w = int(sum(ws) + track * (len(s) - 1)) + 8
    im = Image.new("RGBA", (w, int(size * 1.4)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = 2
    for c, cw in zip(s, ws):
        d.text((x, 2), c, font=f, fill=tuple(color) + (255,))
        x += cw + track
    return im.crop(im.getbbox() or (0, 0, 1, 1))


# ===========================================================================
class Renderer(v2.Renderer):
    def __init__(self, work):
        super().__init__(work)
        self._bw = {}
        self.tiles = None

    # ---- speaker -----------------------------------------------------------
    def speaker(self, i, t, seg):
        w, h = CARD[2], CARD[3]
        col = cv2.imread(os.path.join(self.work, "color2", f"{min(max(i, 1), 1355):04d}.jpg"))
        col = cv2.cvtColor(col, cv2.COLOR_BGR2RGB).astype(np.float32) / 255
        m = np.maximum(self.gray("mask2", i).astype(np.float32) / 255, self.prior)
        pad = SRC_X
        C = cv2.copyMakeBorder(col, 0, 0, pad, 0, cv2.BORDER_REPLICATE)
        Mk = cv2.copyMakeBorder(m, 0, 0, pad, 0, cv2.BORDER_CONSTANT, value=0)
        C = C[-SRC_Y:-SRC_Y + h]; Mk = Mk[-SRC_Y:-SRC_Y + h]
        C[:, :pad + 30] = cv2.GaussianBlur(C, (0, 0), 14)[:, :pad + 30]
        p = (t - seg[0]) / max(seg[1] - seg[0], 0.1)
        k = 1.0 + 0.045 * smooth(p)
        M = cv2.getRotationMatrix2D((w * 0.62, 360), 0, k)
        C = cv2.warpAffine(C, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
        Mk = cv2.warpAffine(Mk, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
        Mk = cv2.GaussianBlur(np.clip((Mk - 0.15) / 0.7, 0, 1), (0, 0), 1.1)
        lum = cv2.GaussianBlur(C.mean(2), (0, 0), 2)
        a = np.clip(lum * 2.6, 0, 1)[..., None] * (0.3 + 0.7 * self.wall)
        ink = np.array(INK, np.float32) / 255
        room = ink * (1 - a) + (LIME / 255 * 0.78) * a
        room = room * (0.5 + 0.5 * self.wall)
        # gentle lime spill on his outline from the lit wall
        sl = np.zeros_like(Mk); sl[:, 6:] = Mk[:, :-6]
        sr = np.zeros_like(Mk); sr[:, :-6] = Mk[:, 6:]
        edge = cv2.GaussianBlur(np.clip(2 * Mk - sl - sr, 0, 1), (0, 0), 3) * Mk * 0.35
        person = C * (1 - edge[..., None]) + (LIME / 255) * np.clip(lum, 0.45, 1)[..., None] * edge[..., None]
        person = np.clip((person - 0.02) * 1.04, 0, 1)
        return room, person, Mk

    def big_rows(self, lines):
        key = ("rows",) + tuple(lines)
        if key in self._bw:
            return self._bw[key]
        w = CARD[2] - 60
        caps = [400] if len(lines) == 1 else [130, 270]
        rows = []
        for ln, cap in zip(lines, caps):
            r = txt(ln, "gothic", 400, WHITE)
            tw = min(w, int(r.width * cap / r.height * 1.9))
            r = r.resize((tw, cap), Image.LANCZOS)
            rows.append(vgrad(r, (255, 255, 255), LIMEt, 1.0, 0.6, mid=((245, 255, 215), 0.45)))
        self._bw[key] = rows
        return rows

    def compose_speaker(self, i, t, seg, t_ov=None):
        t_ov = t if t_ov is None else t_ov
        w, h = CARD[2], CARD[3]
        room, person, m = self.speaker(i, t, seg)
        bg = Image.fromarray((np.clip(room, 0, 1) * 255).astype(np.uint8)).convert("RGBA")
        top_y = 70
        cur = [b for b in BIG if b[0] - 0.01 <= t_ov < b[1]]
        for on, off, lines, kick, align in cur:
            rows = self.big_rows(lines)
            ek = exit_k(t_ov, off)
            hold = smooth((t_ov - on) / max(off - on, 0.5))
            y = top_y + 36
            for r_i, r in enumerate(rows):
                p = expo((t_ov - on - r_i * 0.09) / 0.55)
                sc = (1.06 - 0.06 * p) * (1 + 0.025 * hold)
                place(bg, r, w / 2, y + (1 - p) * 70 - (1 - ek) * 24, alpha=min(1, p * 1.6) * ek,
                      scale=sc, blur=(1 - p) * 9 + (1 - ek) * 6, anchor="ct")
                y += r.height + 10
        bgn = np.asarray(bg.convert("RGB")).astype(np.float32) / 255
        out = bgn * (1 - m[..., None]) + person * m[..., None]
        img = Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8)).convert("RGBA")

        # kicker lines: letter-spacing settles while fading in
        kicks = [(on, off, kick, align) for on, off, lines, kick, align in cur if kick]
        kicks += [k for k in KICK_ONLY if k[0] <= t_ov < k[1]]
        for on, off, kick, align in kicks:
            start = on
            for k in KICK_ONLY:   # a kicker that was already on screen keeps its timing
                if k[2] == kick and k[1] == on:
                    start = k[0]
            p = expo((t_ov - start) / 0.6)
            kt = tracked(kick, "inter", 30, WHITE, 1.0 + (1 - p) * 9)
            kx = w / 2 if align == "c" else 44 + kt.width / 2
            place(img, kt, kx, top_y, alpha=min(1, p * 1.4) * exit_k(t_ov, off), blur=(1 - p) * 3, anchor="ct")

        # captions: small line fades up, big line builds word by word
        for s_on, b_on, off, small, big in CAPS:
            st = min(x for x in (s_on, b_on) if x is not None)
            if not (st <= t_ov < off):
                continue
            ek = exit_k(t_ov, off, 0.18)
            by = 618
            if small and t_ov >= s_on:
                p = expo((t_ov - s_on) / 0.45)
                place(img, txt(small, "urb500", 38, WHITE), w / 2, by - 50 + (1 - p) * 14,
                      alpha=p * ek, blur=(1 - p) * 4, anchor="ct")
            if big and t_ov >= b_on:
                full = fit(txt(big, "gothic", 140, WHITE), w - 70, 88)
                k = full.height / txt(big, "gothic", 140, WHITE).height
                words = big.split(" ")
                ims = [txt(wd, "gothic", 140, WHITE) for wd in words]
                ims = [im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.LANCZOS) for im in ims]
                sp = int(22 * k)
                tw = sum(im.width for im in ims) + sp * (len(ims) - 1)
                x = (w - tw) / 2
                for wi, im in enumerate(ims):
                    p = expo((t_ov - b_on - wi * 0.055) / 0.45)
                    place(img, im, x, by + full.height - im.height + (1 - p) * 26, alpha=min(1, p * 1.5) * ek,
                          blur=(1 - p) * 5)
                    x += im.width + sp

        # frosted-glass checklist
        if CHECKS[0][0] <= t_ov < CHECKS_OFF + 0.5:
            for k_, (on, label) in enumerate(CHECKS):
                if t_ov < on:
                    continue
                p = spring(t_ov - on, 13, 0.75)
                ek = 1.0 if t_ov < CHECKS_OFF else 0.0
                self.glass_pill(img, label, 74 - (1 - p) * 70, 676 + k_ * 74, min(1, p * 1.3) * ek, (1 - clamp01(p)) * 6)

        # bubbles
        for on, off in BUBBLES:
            if on <= t_ov < off:
                ek = exit_k(t_ov, off, 0.22)
                for k_ in range(3):
                    p = spring(t_ov - on - k_ * 0.08, 16, 0.5)
                    if p > 0.01:
                        place(img, self.bubble(), w / 2 + (k_ - 1) * 122, 726 - (1 - ek) * 20,
                              scale=max(p, 0.01) * (0.85 + 0.15 * ek), alpha=ek * min(1, p * 2),
                              rot=(1 - clamp01(p)) * -14, anchor="c")
        return img

    def glass_pill(self, img, label, x, y, alpha, blur):
        if alpha <= 0.01:
            return
        t = txt(label, "urb600", 32, PAPER)
        pw, ph = t.width + 92, 58
        x, y = int(x), int(y)
        # frosted backdrop: blur and darken what is behind the pill
        x0, y0 = max(x, 0), max(y, 0)
        x1, y1 = min(x + pw, img.width), min(y + ph, img.height)
        if x1 <= x0 or y1 <= y0:
            return
        reg = img.crop((x0 - 20 if x0 >= 20 else 0, y0 - 20 if y0 >= 20 else 0, min(x1 + 20, img.width), min(y1 + 20, img.height)))
        rb = reg.filter(ImageFilter.GaussianBlur(14))
        ox, oy = x0 - (x0 - 20 if x0 >= 20 else 0), y0 - (y0 - 20 if y0 >= 20 else 0)
        rb = rb.crop((ox, oy, ox + (x1 - x0), oy + (y1 - y0)))
        arr = np.asarray(rb.convert("RGB")).astype(np.float32)
        arr = arr * 0.45 + np.array(INK, np.float32) * 0.35
        glass = Image.fromarray(arr.clip(0, 255).astype(np.uint8)).convert("RGBA")
        pill = self.pill_shell(pw, ph)
        full = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
        full.paste(glass, (x0 - x, y0 - y))
        full.putalpha(self.pill_mask(pw, ph))
        full.alpha_composite(pill)
        full.alpha_composite(t, (60, (ph - t.height) // 2))
        place(img, full, x, y, alpha=alpha, blur=blur)

    @lru_cache(None)
    def pill_mask(self, w, h):
        return rounded_mask(w, h, h // 2)

    @lru_cache(None)
    def pill_shell(self, w, h):
        S = 4
        im = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((1, 1, w * S - 2, h * S - 2), h * S // 2, outline=(255, 255, 255, 70), width=S * 2)
        cy = h * S // 2
        g = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
        ImageDraw.Draw(g).ellipse((22 * S, cy - 14 * S, 50 * S, cy + 14 * S), fill=LIMEt + (120,))
        g = g.filter(ImageFilter.GaussianBlur(6 * S))
        im.alpha_composite(g)
        d.ellipse((28 * S, cy - 8 * S, 44 * S, cy + 8 * S), fill=LIMEt + (255,))
        return im.resize((w, h), Image.LANCZOS)

    @lru_cache(None)
    def bubble(self):
        r = 52
        S = 4
        size = (r * 2 + 40)
        im = Image.new("RGBA", (size * S, size * S), (0, 0, 0, 0))
        sh_ = Image.new("L", im.size, 0)
        ImageDraw.Draw(sh_).ellipse((20 * S, 28 * S, (20 + 2 * r) * S, (28 + 2 * r) * S), fill=150)
        sh_ = sh_.filter(ImageFilter.GaussianBlur(9 * S))
        shl = Image.new("RGBA", im.size, (0, 0, 0, 0)); shl.putalpha(sh_)
        im.alpha_composite(shl)
        circ = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(circ).ellipse((20 * S, 20 * S, (20 + 2 * r) * S, (20 + 2 * r) * S), fill=(250, 250, 246, 255))
        # soft top highlight
        hl = Image.new("L", im.size, 0)
        ImageDraw.Draw(hl).ellipse((32 * S, 24 * S, (8 + 2 * r) * S, (20 + r) * S), fill=60)
        hl = hl.filter(ImageFilter.GaussianBlur(8 * S))
        im.alpha_composite(circ)
        hlw = Image.new("RGBA", im.size, (255, 255, 255, 0)); hlw.putalpha(hl)
        im.alpha_composite(hlw)
        ImageDraw.Draw(im).ellipse((20 * S, 20 * S, (20 + 2 * r) * S, (20 + 2 * r) * S), outline=LIMEt + (255,), width=4 * S)
        im = im.resize((size, size), Image.LANCZOS)
        q = txt("?", "urb800", 70, INK)
        im.alpha_composite(q, ((size - q.width) // 2, (size - q.height) // 2 - 2))
        return im

    # ---- number cards ---------------------------------------------------------
    def compose_number(self, t, n):
        w, h = CARD[2], CARD[3]
        img = self.vig.copy()
        breathe = 1 + 0.02 * smooth((t - v1.seg_at(t)[0]) / 2.0)
        if breathe > 1.001:
            cw, ch = int(w * breathe), int(h * breathe)
            img = img.resize((cw, ch), Image.BICUBIC).crop(((cw - w) // 2, (ch - h) // 2, (cw - w) // 2 + w, (ch - h) // 2 + h))
        t_num, (small, t_s), (title, t_t) = NUM_CARDS[n]
        ti = fit(txt(title, "gothic", 300, INK), 300 if n != 3 else 270, 108 if n != 3 else 86)
        ti = vgrad(ti, (24, 26, 16), (24, 26, 16))
        si = txt(small, "urb400", 42, GREY)
        nh = ti.height + si.height + 14
        nr = txt(str(n), "anton", 300, WHITE)
        num = hgrad(nr.resize((int(nr.width * nh / nr.height), nh), Image.LANCZOS), (236, 255, 170), (150, 200, 10))
        gw = num.width + 18 + max(ti.width, si.width)
        x0 = (w - gw) / 2
        ybot = 500
        tx = x0 + num.width + 18
        key = ("ls", n)
        if key not in self._bw:
            comp = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            comp.alpha_composite(num, (int(x0), int(ybot - num.height)))
            comp.alpha_composite(ti, (int(tx), int(ybot - ti.height)))
            self._bw[key] = long_shadow(comp, 160, 0.085)
        if t >= t_t:
            place(img, self._bw[key], 0, 0, alpha=smooth((t - t_t) / 0.6))
        if t >= t_num:
            p = expo((t - t_num) / 0.6)
            vis = max(1, int(num.height * min(1, p * 1.05)))
            part = num.crop((0, 0, num.width, vis))
            place(img, part, x0, ybot - num.height + (1 - p) * 40, blur=(1 - p) * 6)
        if t >= t_s:
            p = expo((t - t_s) / 0.5)
            place(img, si, tx, ybot - ti.height - si.height - 12 + (1 - p) * 16, alpha=p, blur=(1 - p) * 4)
        if t >= t_t:
            p = expo((t - t_t) / 0.55)
            # feathered wipe, left to right
            a = np.asarray(ti.getchannel("A")).astype(np.float32)
            xs = np.arange(ti.width)[None, :]
            edge = p * (ti.width + 60) - 60
            a = a * np.clip((edge - xs) / 60 + 1, 0, 1)
            tw = ti.copy(); tw.putalpha(Image.fromarray(a.astype(np.uint8)))
            place(img, tw, tx, ybot - ti.height)
            q = expo((t - t_t - 0.25) / 0.5)
            if q > 0.01:
                ImageDraw.Draw(img).rounded_rectangle((tx, ybot + 16, tx + ti.width * q, ybot + 24), 4, fill=LIMEt + (255,))
        return img

    # ---- inspiration: mood board ------------------------------------------------
    def make_tiles(self):
        tiles = []
        tw, th = 138, 176
        S = 3
        def base(fill):
            im = Image.new("RGBA", (tw * S, th * S), (0, 0, 0, 0))
            ImageDraw.Draw(im).rounded_rectangle((0, 0, tw * S - 1, th * S - 1), 16 * S, fill=fill + (255,))
            return im
        # 1 type specimen
        im = base(INK); f = font("gothic", 150 * S)
        ImageDraw.Draw(im).text((16 * S, 10 * S), "Aa", font=f, fill=LIMEt + (255,))
        tiles.append(im)
        # 2 palette
        im = base(PAPER); d = ImageDraw.Draw(im)
        for k, c in enumerate((INK, LIMEt, LIME_DEEP, (214, 212, 205))):
            d.rounded_rectangle((14 * S, (14 + k * 38) * S, (tw - 14) * S, (44 + k * 38) * S), 8 * S, fill=c + (255,))
        tiles.append(im)
        # 3 a frame of his footage
        fr = cv2.cvtColor(cv2.imread(os.path.join(self.work, "color2", "0700.jpg")), cv2.COLOR_BGR2RGB)
        fr = Image.fromarray(fr[180:180 + 600, 0:448]).resize((tw * S, th * S), Image.LANCZOS).convert("RGBA")
        fr.putalpha(rounded_mask(tw * S, th * S, 16 * S))
        tiles.append(fr)
        # 4 layout grid
        im = base((250, 251, 246)); d = ImageDraw.Draw(im)
        for k in range(1, 4):
            d.line((k * tw * S / 4, 12 * S, k * tw * S / 4, (th - 12) * S), fill=(200, 200, 190, 255), width=S)
            d.line((12 * S, k * th * S / 4, (tw - 12) * S, k * th * S / 4), fill=(200, 200, 190, 255), width=S)
        d.ellipse((tw * S / 4, th * S / 4, tw * S * 3 / 4, th * S / 4 + tw * S / 2), fill=LIMEt + (255,))
        tiles.append(im)
        # 5 light leak
        g = np.zeros((th * S, tw * S, 3), np.float32)
        yy, xx = np.mgrid[0:th * S, 0:tw * S].astype(np.float32)
        lk = np.exp(-(((xx - tw * S * 0.8) / (tw * S * 0.5)) ** 2 + ((yy - th * S * 0.2) / (th * S * 0.45)) ** 2))[..., None]
        g = np.array(INK, np.float32) * (1 - lk) + np.array(LIMEt, np.float32) * lk
        im = Image.fromarray(g.astype(np.uint8)).convert("RGBA"); im.putalpha(rounded_mask(tw * S, th * S, 16 * S))
        tiles.append(im)
        # 6 headline sample
        im = base(LIMEt); d = ImageDraw.Draw(im)
        d.text((14 * S, 14 * S), "EVERY\nFRAME", font=font("gothic", 64 * S), fill=INK + (255,), spacing=0)
        d.rounded_rectangle((14 * S, (th - 30) * S, (tw - 60) * S, (th - 22) * S), 4 * S, fill=INK + (255,))
        tiles.append(im)
        out = []
        for im in tiles:
            im = im.resize((tw, th), Image.LANCZOS)
            sh_ = Image.new("RGBA", (tw + 40, th + 40), (0, 0, 0, 0))
            m = Image.new("L", (tw + 40, th + 40), 0); m.paste(rounded_mask(tw, th, 16), (20, 26))
            sh_.putalpha(m.filter(ImageFilter.GaussianBlur(9)).point(lambda v: int(v * 0.28)))
            sh_.alpha_composite(im, (20, 20))
            out.append(sh_)
        return out

    def compose_insp(self, t):
        if self.tiles is None:
            self.tiles = self.make_tiles()
        w, h = CARD[2], CARD[3]
        img = self.soft.copy()
        T = INSP
        # "thousands": a faint dense grid fades in behind
        if t >= T["more"]:
            p = smooth((t - T["more"]) / 0.8)
            lay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            d = ImageDraw.Draw(lay)
            for r in range(16):
                for c in range(9):
                    if (r * 7 + c * 3) % 5 == 0:
                        continue
                    x, y = 14 + c * 58, 230 + r * 34 - (t - T["more"]) * 18
                    d.rounded_rectangle((x, y, x + 50, y + 26), 5, fill=(110, 140, 20, int(22 * p)))
            img.alpha_composite(lay)
        if t >= T["vault"]:
            p = expo((t - T["vault"]) / 0.6)
            ins = vgrad(fit(txt("INSPIRATION", "gothic", 300, INK), 400, 112), (24, 26, 16), LIME_DEEP)
            place(img, ins, w / 2, 96 + (1 - p) * 30, alpha=p, blur=(1 - p) * 6, anchor="ct")
            place(img, txt("vault", "urb400", 36, GREY), w / 2, 96 + ins.height + 8 + (1 - p) * 20, alpha=p, anchor="ct")
            zoom = 1 + 0.07 * expo((t - T["house"]) / 0.7) if t >= T["house"] else 1
            drift = (t - T["vault"]) * 6
            cx, cy = w / 2, 492
            for k, tile in enumerate(self.tiles):
                r_, c_ = divmod(k, 3)
                q = spring(t - T["vault"] - 0.1 - k * 0.07, 12, 0.7)
                if q <= 0.01:
                    continue
                bx = (c_ - 1) * 156
                by = (r_ - 0.5) * 196 + (c_ - 1) * 14
                x = cx + bx * zoom + (1 if c_ % 2 else -1) * drift * 0.4
                y = cy + by * zoom + (1 - q) * 120 - drift * (0.6 if c_ == 1 else 0.3)
                place(img, tile, x, y, alpha=min(1, q * 1.4), scale=zoom * (0.9 + 0.1 * min(q, 1)),
                      rot=((k % 3) - 1) * 3.5 * min(q, 1.2), blur=(1 - clamp01(q)) * 6, anchor="c")
        if t >= T["refs"]:
            p = expo((t - T["refs"]) / 0.55)
            s = txt("thousands of", "urb400", 34, GREY)
            r = vgrad(fit(txt("REFERENCES", "gothic", 300, INK), 400, 104), (24, 26, 16), LIME_DEEP)
            place(img, s, w / 2, 748 + (1 - p) * 16, alpha=p, blur=(1 - p) * 4, anchor="ct")
            place(img, r, w / 2, 748 + s.height + 10 + (1 - p) * 24, alpha=p, blur=(1 - p) * 6, anchor="ct")
        return img

    # ---- effect list ------------------------------------------------------------
    def compose_fx(self, t):
        w, h = CARD[2], CARD[3]
        img = self.soft_card_live(t)
        hd = tracked("EFFECTS", "inter", 24, GREY, 6)
        p0 = expo((t - 36.9) / 0.6)
        place(img, hd, 64, 170 + (1 - p0) * 10, alpha=p0)
        for k, (on, label) in enumerate(FX_ROWS):
            if t < on:
                continue
            p = spring(t - on, 13, 0.72)
            tog = spring(t - on - 0.22, 18, 0.6)
            row = self.fx_row(label, round(clamp01(tog) * 12) / 12)
            place(img, row, 44 + (1 - p) * 90, 214 + k * 104, alpha=min(1, p * 1.4), blur=(1 - clamp01(p)) * 6)
        return img

    def soft_card_live(self, t):
        """FX card background with the two lime plus shapes drifting slowly."""
        w, h = CARD[2], CARD[3]
        img = self.soft.copy()
        for (cx, cy, r, ph) in ((44, 40, 66, 0.0), (w - 52, h - 86, 60, 1.7)):
            ang = 18 + 10 * math.sin(t * 0.9 + ph)
            dy = 8 * math.sin(t * 1.1 + ph)
            p = self.plus_shape(r).rotate(ang, resample=Image.BICUBIC, expand=True)
            img.alpha_composite(p, (int(cx - p.width / 2), int(cy + dy - p.height / 2)))
        return img

    @lru_cache(None)
    def plus_shape(self, r):
        S = 3
        c = r * 1.6
        p = Image.new("RGBA", (int(c * 2 * S), int(c * 2 * S)), (0, 0, 0, 0))
        d = ImageDraw.Draw(p)
        C = c * S; R = r * S
        d.rounded_rectangle((C - R, C - R * 0.36, C + R, C + R * 0.36), R * 0.3, fill=LIMEt + (255,))
        d.rounded_rectangle((C - R * 0.36, C - R, C + R * 0.36, C + R), R * 0.3, fill=LIMEt + (255,))
        p = p.resize((int(c * 2), int(c * 2)), Image.LANCZOS)
        return p.filter(ImageFilter.GaussianBlur(4))

    @lru_cache(None)
    def fx_row(self, label, on):
        rw, rh = CARD[2] - 88, 84
        S = 3
        im = Image.new("RGBA", ((rw + 40) * S, (rh + 40) * S), (0, 0, 0, 0))
        sh_ = Image.new("L", im.size, 0)
        ImageDraw.Draw(sh_).rounded_rectangle((20 * S, 28 * S, (20 + rw) * S, (28 + rh) * S), 22 * S, fill=70)
        shl = Image.new("RGBA", im.size, (40, 52, 10, 0)); shl.putalpha(sh_.filter(ImageFilter.GaussianBlur(12 * S)))
        im.alpha_composite(shl)
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((20 * S, 20 * S, (20 + rw) * S, (20 + rh) * S), 22 * S, fill=(255, 255, 255, 215),
                            outline=(255, 255, 255, 255), width=2 * S)
        # toggle
        tw, th = 74, 40
        tx, ty = 20 + rw - tw - 22, 20 + (rh - th) // 2
        track = tuple(int(a + (b - a) * on) for a, b in zip((222, 222, 214), LIMEt))
        d.rounded_rectangle((tx * S, ty * S, (tx + tw) * S, (ty + th) * S), th * S // 2, fill=track + (255,))
        kx = tx + 4 + on * (tw - th)
        d.ellipse((kx * S, (ty + 4) * S, (kx + th - 8) * S, (ty + th - 4) * S), fill=(INK if on > 0.5 else WHITE) + (255,))
        im = im.resize((rw + 40, rh + 40), Image.LANCZOS)
        lab = txt(label, "urb600", 32, INK)
        im.alpha_composite(lab, (20 + 28, 20 + (rh - lab.height) // 2))
        return im

    # ---- frame + transitions -------------------------------------------------------
    def content(self, seg, t, i, t_ov):
        kind = seg[2]
        if kind == "spk":
            return self.compose_speaker(i, t, seg, t_ov)
        if kind == "num":
            return self.compose_number(t_ov, seg[3])
        if kind == "insp":
            return self.compose_insp(t_ov)
        return self.compose_fx(t_ov)

    def frame(self, fi):
        t = fi / FPS
        i = fi + 1
        seg = v1.seg_at(t)
        near = [b for b in BOUNDS if abs(t - b) < TR]
        if near:
            b = near[0]
            k = SEGMENTS.index(next(s for s in SEGMENTS if abs(s[0] - b) < 1e-6))
            prev, nxt = SEGMENTS[k - 1], SEGMENTS[k]
            u = smooth((t - (b - TR)) / (2 * TR))
            A = self.content(prev, t, i, min(t, b - 1 / FPS))
            B = self.content(nxt, t, i, max(t, b))
            A = self.zoom(A, 1 + 0.12 * u, 9 * u)
            B = self.zoom(B, 0.9 + 0.1 * u, 9 * (1 - u))
            A = np.asarray(A.convert("RGB")).astype(np.float32)
            B = np.asarray(B.convert("RGB")).astype(np.float32)
            content = Image.fromarray((A * (1 - u) + B * u).astype(np.uint8)).convert("RGBA")
        else:
            content = self.content(seg, t, i, t)
        content.putalpha(self.card_mask)
        page = self.page.copy()
        bf = Image.fromarray(self.gray("before_up", i)).convert("RGBA")
        bf.putalpha(self.before_mask)
        page.alpha_composite(bf, (BEFORE[0], BEFORE[1]))
        page.alpha_composite(self.card_shadow[0], self.card_shadow[1])
        page.alpha_composite(content, (CARD[0], CARD[1]))
        return np.asarray(page.convert("RGB"))

    @staticmethod
    def zoom(im, k, blur):
        w, h = im.size
        if abs(k - 1) > 1e-3:
            cw, ch = int(w * k), int(h * k)
            z = im.resize((cw, ch), Image.BILINEAR)
            if k > 1:
                im = z.crop(((cw - w) // 2, (ch - h) // 2, (cw - w) // 2 + w, (ch - h) // 2 + h))
            else:
                base = im.filter(ImageFilter.GaussianBlur(20))
                base.alpha_composite(z, ((w - cw) // 2, (h - ch) // 2))
                im = base
        if blur > 0.5:
            im = im.filter(ImageFilter.GaussianBlur(blur))
        return im


# ===========================================================================
SR = 48000


def build_audio(work, music, start, out_wav):
    import soundfile as sf
    from scipy.signal import butter, sosfilt, resample_poly
    n = int(END * SR)
    v, sr = sf.read(os.path.join(work, "voice.wav"), dtype="float32")
    v = v.mean(1) if v.ndim > 1 else v
    if sr != SR:
        v = resample_poly(v, SR, sr).astype(np.float32)
    v = np.pad(v, (0, max(0, n - len(v))))[:n]
    v = sosfilt(butter(2, 75, "high", fs=SR, output="sos"), v)
    v = v / (np.abs(v).max() + 1e-9) * 0.7
    raw = subprocess.run(f'ffmpeg -v error -ss {start} -i "{music}" -t {END + 0.5} -ac 2 -ar {SR} -f f32le -',
                         shell=True, check=True, capture_output=True).stdout
    mu = np.frombuffer(raw, np.float32).reshape(-1, 2)
    mu = np.pad(mu, ((0, max(0, n - len(mu))), (0, 0)))[:n].copy()
    tt = np.arange(n) / SR
    mu *= np.clip(tt / 0.03, 0, 1)[:, None] * np.clip((END - tt) / 1.6, 0, 1)[:, None]
    # music sits under the voice: base level, then a soft duck while he speaks
    mu = mu / (np.sqrt(np.mean(mu ** 2)) + 1e-9) * np.sqrt(np.mean(v ** 2)) * 0.32
    env = np.abs(v)
    env = sosfilt(butter(1, 6, "low", fs=SR, output="sos"), env)
    env = env / (np.percentile(env, 95) + 1e-9)
    duck = 10 ** (-5 * np.clip(env, 0, 1) / 20)
    duck = sosfilt(butter(1, 3, "low", fs=SR, output="sos"), duck)
    mu *= duck[:, None]
    fx = np.zeros(n)
    rng = np.random.default_rng(7)
    for t0, kind in SFX:
        x, pre = v1.make_sfx(kind, rng)
        s = int((t0 - pre) * SR)
        if s < 0:
            x = x[-s:]; s = 0
        e = min(n, s + len(x))
        fx[s:e] += x[:e - s]
    fx *= 0.12
    mix = np.stack([v + fx, v + fx], 1) + mu
    sf.write(out_wav, mix.astype(np.float32), SR)


R = None


def _init(work):
    global R
    v2.FD = v2.fonts_dir(work)
    R = Renderer(work)


def _frame(fi):
    return R.frame(fi).tobytes()


def render(work, music=None, start=24.0, only=None):
    from multiprocessing import Pool
    if not os.path.exists(os.path.join(work, "mask_prior.png")):
        v2.mask_prior(work)
    nfr = int(round(END * FPS))
    if only is not None:
        _init(work)
        for fi in only:
            Image.fromarray(R.frame(fi)).save(os.path.join(work, f"v3_{fi:04d}.png"))
        return
    vid = os.path.join(work, "video_v3.mp4")
    p = subprocess.Popen(f'ffmpeg -v error -y -f rawvideo -pix_fmt rgb24 -s {W}x{H} -r {FPS} -i - '
                         f'-c:v libx264 -preset slow -crf 15 -pix_fmt yuv420p "{vid}"', shell=True, stdin=subprocess.PIPE)
    with Pool(3, initializer=_init, initargs=(work,)) as pool:
        for k, buf in enumerate(pool.imap(_frame, range(nfr), chunksize=4)):
            p.stdin.write(buf)
            if k % 300 == 0:
                print(f"frame {k}/{nfr}", flush=True)
    p.stdin.close(); p.wait()
    mix, master = os.path.join(work, "mix_v3.wav"), os.path.join(work, "master_v3.wav")
    build_audio(work, music, start, mix)
    v1.loudnorm(mix, master)
    out = os.path.join(work, "AVE_Before_After_V3.mp4")
    sh(f'ffmpeg -v error -y -i "{vid}" -i "{master}" -c:v copy -c:a aac -b:a 256k -shortest -movflags +faststart "{out}"')
    print(out)


if __name__ == "__main__":
    cmd, ref, work = sys.argv[1:4]
    if cmd == "render":
        render(work, sys.argv[4], float(sys.argv[5]) if len(sys.argv) > 5 else 24.0)
    elif cmd == "stills":
        render(work, only=[int(round(float(x) * FPS)) for x in sys.argv[4:]])
