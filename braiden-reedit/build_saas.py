"""AVE Studio · SaaS-style talking-head breakdown of Braiden Shaw's clip.

Layout (1080x1920, follows the breakdown format of the reference reel, in AVE
colours): "Final video" card (our SaaS-style edit), "Raw video" card, "Script"
card with the transcript lighting up word by word, and a "Timeline" card that
draws this edit's real tracks with a moving playhead; DM "SAMPLE" footer.

The final video: Braiden cut out onto a clean light studio background, with
glassy UI cards acting out what he says (toggle, balance card, shopping list,
search bar, upgrade button with cursor, product cards, a draining happiness
meter), big words behind him and karaoke captions. Everything is drawn here.

Needs the WORK dir prepared by build.py / build_v2.py (raw/, mask/, voice.wav,
words.json, broll/) — see those files.

Usage: python build_saas.py render SOURCE.mp4 WORK [MUSIC.mp3 START]
       python build_saas.py stills SOURCE.mp4 WORK 1.0 ...
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
OLIVE = (96, 128, 8)
G300, G500, G700 = (214, 212, 205), (138, 135, 127), (58, 57, 54)
WHITE = (255, 255, 255)
FONTS = os.path.join(b1.ROOT, "ave-promo", "film", "fonts")

FINAL = (85, 252, 450, 806)
RAWC = (558, 252, 441, 441)
SCRIPT = (558, 720, 441, 333)
TIMEL = (85, 1107, 914, 441)
RAD = 40
FW, FH = FINAL[2], FINAL[3]


@lru_cache(None)
def font(kind, size):
    files = {"xb": "InterDisplay-ExtraBold.otf", "b": "InterDisplay-Bold.otf", "sb": "InterDisplay-SemiBold.otf",
             "md": "InterDisplay-Medium.otf", "serif": "InstrumentSerif-italic-400.woff2",
             "mono": "JetBrainsMono-normal-500.woff2", "mono6": "JetBrainsMono-normal-600.woff2"}
    return ImageFont.truetype(os.path.join(FONTS, files[kind]), size)


@lru_cache(None)
def txt(s, kind, size, color, track=0):
    f = font(kind, size)
    asc, desc = f.getmetrics()
    if track:
        ws = [f.getlength(c) for c in s]
        im = Image.new("RGBA", (int(sum(ws) + track * len(s)) + 12, asc + desc + 4), (0, 0, 0, 0))
        d = ImageDraw.Draw(im); x = 2
        for c, cw in zip(s, ws):
            d.text((x, 2), c, font=f, fill=color + (255,)); x += cw + track
    else:
        im = Image.new("RGBA", (int(f.getlength(s)) + 12, asc + desc + 4), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((2, 2), s, font=f, fill=color + (255,))
    bb = im.getbbox() or (0, 0, 1, 1)
    return im.crop((bb[0], 0, bb[2], im.height))


def rmask(w, h, r, ss=3):
    m = Image.new("L", (w * ss, h * ss), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w * ss - 1, h * ss - 1), r * ss, fill=255)
    return m.resize((w, h), Image.LANCZOS)


def soft_shadow(w, h, r, blur=22, a=0.16, oy=14, color=(40, 44, 20)):
    p = blur * 2 + 10
    m = Image.new("L", (w + 2 * p, h + 2 * p), 0)
    m.paste(rmask(w, h, r), (p, p + oy))
    m = m.filter(ImageFilter.GaussianBlur(blur))
    s = Image.new("RGBA", m.size, color + (0,))
    s.putalpha(m.point(lambda v: int(v * a)))
    return s, p


# ---- line glyphs ------------------------------------------------------------------
@lru_cache(None)
def glyph(kind, size, color=INK, lw=None):
    S = 4
    s = size * S
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = color + (255,)
    lw = (lw or max(2, size // 11)) * S
    if kind == "bag":
        d.rounded_rectangle((s * .18, s * .32, s * .82, s * .9), s * .08, outline=c, width=lw)
        d.arc((s * .32, s * .1, s * .68, s * .5), 180, 360, fill=c, width=lw)
    elif kind == "watch":
        d.rounded_rectangle((s * .36, s * .05, s * .64, s * .95), s * .06, outline=c, width=lw)
        d.ellipse((s * .22, s * .28, s * .78, s * .72), fill=WHITE + (255,), outline=c, width=lw)
        d.line((s * .5, s * .5, s * .5, s * .36), fill=c, width=lw); d.line((s * .5, s * .5, s * .6, s * .55), fill=c, width=lw)
    elif kind == "shoe":
        d.line([(s * .1, s * .7), (s * .1, s * .35), (s * .35, s * .35), (s * .55, s * .55), (s * .88, s * .6),
                (s * .9, s * .78), (s * .1, s * .78), (s * .1, s * .7)], fill=c, width=lw, joint="curve")
    elif kind == "search":
        d.ellipse((s * .12, s * .12, s * .66, s * .66), outline=c, width=lw)
        d.line((s * .58, s * .58, s * .88, s * .88), fill=c, width=lw)
    elif kind == "check":
        d.line([(s * .2, s * .52), (s * .42, s * .74), (s * .82, s * .3)], fill=c, width=lw, joint="curve")
    elif kind == "heart":
        d.polygon([(s * .5, s * .86), (s * .1, s * .45), (s * .5, s * .3), (s * .9, s * .45)], fill=c)
        d.ellipse((s * .1, s * .18, s * .52, s * .6), fill=c); d.ellipse((s * .48, s * .18, s * .9, s * .6), fill=c)
    elif kind == "wallet":
        d.rounded_rectangle((s * .1, s * .25, s * .9, s * .82), s * .1, outline=c, width=lw)
        d.rounded_rectangle((s * .55, s * .42, s * .9, s * .65), s * .06, outline=c, width=lw)
    elif kind == "cursor":
        d.polygon([(s * .2, s * .08), (s * .2, s * .82), (s * .4, s * .64), (s * .55, s * .94), (s * .66, s * .89),
                   (s * .52, s * .6), (s * .78, s * .6)], fill=INK + (255,), outline=WHITE + (255,))
    return im.resize((size, size), Image.LANCZOS)


# ---- UI components (each returns an RGBA image) -------------------------------------------
def card_base(w, h, r=24, fill=(255, 255, 255, 214), border=(255, 255, 255, 255)):
    sh, p = soft_shadow(w, h, r, 18, 0.14, 12)
    im = Image.new("RGBA", sh.size, (0, 0, 0, 0))
    im.alpha_composite(sh)
    body = Image.new("RGBA", (w, h), fill)
    body.putalpha(Image.fromarray((np.asarray(rmask(w, h, r)).astype(np.float32) * fill[3] / 255).astype(np.uint8)))
    im.alpha_composite(body, (p, p))
    ImageDraw.Draw(im).rounded_rectangle((p, p, p + w - 1, p + h - 1), r, outline=border, width=2)
    return im, p


@lru_cache(None)
def chip(label, fill, fg, tilt=-6):
    t = txt(label, "sb", 30, fg)
    w, h = t.width + 52, 56
    S = 3
    im = Image.new("RGBA", ((w + 60) * S, (h + 60) * S), (0, 0, 0, 0))
    gl = Image.new("L", im.size, 0)
    ImageDraw.Draw(gl).rounded_rectangle((30 * S, 30 * S, (30 + w) * S, (30 + h) * S), h * S // 2, fill=120)
    gl = gl.filter(ImageFilter.GaussianBlur(14 * S))
    g = Image.new("RGBA", im.size, fill + (0,)); g.putalpha(gl); im.alpha_composite(g)
    ImageDraw.Draw(im).rounded_rectangle((30 * S, 30 * S, (30 + w) * S, (30 + h) * S), h * S // 2, fill=fill + (255,))
    im = im.resize((w + 60, h + 60), Image.LANCZOS)
    im.alpha_composite(t, (30 + 26, 30 + (h - t.height) // 2))
    return im.rotate(-tilt, resample=Image.BICUBIC, expand=True)


def ui_toggle(on):
    im, p = card_base(260, 84, 22)
    d = ImageDraw.Draw(im)
    lab = txt("Stand by it", "sb", 28, INK)
    im.alpha_composite(lab, (p + 22, p + (84 - lab.height) // 2))
    tw, th = 70, 38
    tx, ty = p + 260 - tw - 20, p + (84 - th) // 2
    track = tuple(int(a + (b - a) * on) for a, b in zip(G300, LIME))
    d.rounded_rectangle((tx, ty, tx + tw, ty + th), th // 2, fill=track + (255,))
    kx = tx + 4 + on * (tw - th)
    d.ellipse((kx, ty + 4, kx + th - 8, ty + th - 4), fill=(INK if on > .5 else WHITE) + (255,))
    return im


def ui_balance(value, delta=None, spark=1.0):
    w, h = 300, 168
    im, p = card_base(w, h, 26)
    d = ImageDraw.Draw(im)
    im.alpha_composite(glyph("wallet", 26), (p + 22, p + 22))
    im.alpha_composite(txt("BALANCE", "mono", 20, G500, track=3), (p + 58, p + 26))
    im.alpha_composite(txt(f"${int(value):,}", "xb", 54, INK), (p + 22, p + 58))
    if delta:
        dl = txt(delta, "sb", 22, INK)
        bw = dl.width + 24
        d.rounded_rectangle((p + w - bw - 18, p + 20, p + w - 18, p + 52), 16, fill=LIME + (255,))
        im.alpha_composite(dl, (p + w - bw - 6, p + 20 + (32 - dl.height) // 2))
    # sparkline
    pts = [(p + 22 + k * (w - 44) / 11, p + h - 22 - 22 * (0.3 + 0.7 * (k / 11) ** 1.6 + 0.12 * math.sin(k * 1.7)))
           for k in range(12)]
    n = max(2, int(len(pts) * clamp01(spark)))
    d.line(pts[:n], fill=OLIVE + (255,), width=3, joint="curve")
    return im


def ui_list(items, show):
    w, rowh = 290, 62
    h = 60 + rowh * len(items)
    im, p = card_base(w, h, 26)
    d = ImageDraw.Draw(im)
    im.alpha_composite(txt("SPENT ON", "mono", 20, G500, track=3), (p + 22, p + 22))
    for k, (ic, name, price) in enumerate(items):
        q = clamp01(show - k)
        if q <= 0:
            continue
        y = p + 56 + k * rowh
        a = int(255 * q)
        d.rounded_rectangle((p + 18, y, p + 62, y + 44), 12, fill=PAPER + (a,))
        g = glyph(ic, 28).copy(); g.putalpha(g.getchannel("A").point(lambda v: int(v * q)))
        im.alpha_composite(g, (p + 26, y + 8))
        nm = txt(name, "sb", 26, INK).copy(); pr = txt(price, "md", 26, G500).copy()
        nm.putalpha(nm.getchannel("A").point(lambda v: int(v * q))); pr.putalpha(pr.getchannel("A").point(lambda v: int(v * q)))
        im.alpha_composite(nm, (p + 76, y + (44 - nm.height) // 2))
        im.alpha_composite(pr, (p + w - 22 - pr.width, y + (44 - pr.height) // 2))
    return im


def ui_search(typed, caret, result):
    w, h = 360, 80
    im, p = card_base(w, h + (70 if result > 0 else 0), 28)
    d = ImageDraw.Draw(im)
    im.alpha_composite(glyph("search", 28), (p + 22, p + (h - 28) // 2))
    t = txt(typed or " ", "md", 28, INK)
    im.alpha_composite(t, (p + 64, p + (h - t.height) // 2))
    if caret:
        x = p + 66 + t.width
        d.rectangle((x, p + 24, x + 2, p + h - 24), fill=INK + (255,))
    if result > 0:
        y = p + h + 6
        d.line((p + 18, p + h, p + w - 18, p + h), fill=G300 + (255,), width=2)
        r = txt("No results found", "sb", 26, G500).copy()
        r.putalpha(r.getchannel("A").point(lambda v: int(v * result)))
        im.alpha_composite(r, (p + 22, y + 14))
    return im


def ui_button(pressed):
    w, h = 220, 76
    S = 3
    sc = 1 - 0.06 * pressed
    im, p = card_base(w, h, h // 2, fill=LIME + (255,), border=LIME + (255,))
    lab = txt("Upgrade", "b", 30, INK)
    im.alpha_composite(lab, (p + (w - lab.width) // 2, p + (h - lab.height) // 2))
    if abs(sc - 1) > 1e-3:
        im = im.resize((int(im.width * sc), int(im.height * sc)), Image.LANCZOS)
    return im


@lru_cache(None)
def ui_product(key, label, work):
    w, h = 186, 236
    im, p = card_base(w, h, 24)
    ph = Image.open(os.path.join(work, "broll", key + ".jpg")).convert("RGB")
    pw_, ph_ = w - 24, 140
    r = ph.width / ph.height
    cw = int(ph.height * pw_ / ph_)
    x0 = (ph.width - cw) // 2
    ph = ph.crop((x0, 0, x0 + cw, ph.height)).resize((pw_, ph_), Image.LANCZOS).convert("RGBA")
    ph.putalpha(rmask(pw_, ph_, 16))
    im.alpha_composite(ph, (p + 12, p + 12))
    im.alpha_composite(txt(label, "b", 28, INK), (p + 16, p + 166))
    im.alpha_composite(txt("Upgraded", "md", 20, G500), (p + 16, p + 200))
    d = ImageDraw.Draw(im)
    d.ellipse((p + w - 50, p + 172, p + w - 16, p + 206), fill=LIME + (255,))
    im.alpha_composite(glyph("check", 24), (p + w - 45, p + 177))
    return im


def ui_meter(level):
    w, h = 300, 112
    im, p = card_base(w, h, 24)
    d = ImageDraw.Draw(im)
    im.alpha_composite(glyph("heart", 24), (p + 22, p + 22))
    im.alpha_composite(txt("HAPPINESS", "mono", 20, G500, track=3), (p + 56, p + 24))
    pc = txt(f"{int(round(level * 100))}%", "b", 26, INK)
    im.alpha_composite(pc, (p + w - 22 - pc.width, p + 20))
    bx, by, bw, bh = p + 22, p + 68, w - 44, 18
    d.rounded_rectangle((bx, by, bx + bw, by + bh), 9, fill=PAPER + (255,))
    if level > 0.01:
        d.rounded_rectangle((bx, by, bx + max(bh, bw * level), by + bh), 9, fill=(LIME if level > 0.35 else G500) + (255,))
    return im


@lru_cache(None)
def avatar(k):
    S = 3
    r = 30
    im = Image.new("RGBA", (2 * r * S, 2 * r * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cols = [(220, 214, 200), LIME, (190, 196, 180), (232, 228, 218)]
    d.ellipse((0, 0, 2 * r * S - 1, 2 * r * S - 1), fill=cols[k % 4] + (255,), outline=WHITE + (255,), width=4 * S)
    d.ellipse((r * S - 10 * S, 12 * S, r * S + 10 * S, 32 * S), fill=G700 + (255,))
    d.pieslice((r * S - 22 * S, 36 * S, r * S + 22 * S, 80 * S), 180, 360, fill=G700 + (255,))
    im = im.resize((2 * r, 2 * r), Image.LANCZOS)
    m = Image.new("L", im.size, 0); ImageDraw.Draw(m).ellipse((0, 0, 2 * r - 1, 2 * r - 1), fill=255)
    a = np.minimum(np.asarray(im.getchannel("A")), np.asarray(m)); im.putalpha(Image.fromarray(a))
    return im


# ===========================================================================
class Renderer:
    def __init__(self, work):
        self.work = work
        self.words = [(a, b, w) for a, b, w in json.load(open(os.path.join(work, "words.json")))]
        self.page = self.build_page()
        self.final_mask = rmask(FW, FH, RAD)
        self.raw_mask = rmask(RAWC[2], RAWC[3], RAD)
        yy, xx = np.mgrid[0:FH, 0:FW].astype(np.float32)
        g = np.exp(-(((xx - FW * 0.5) / (FW * 0.55)) ** 2 + ((yy - FH * 0.42) / (FH * 0.35)) ** 2))
        bg = np.array((248, 247, 243), np.float32) * (1 - 0.06 * (yy / FH)[..., None])
        bg = bg * (1 - g[..., None] * 0.18) + np.array(LIME, np.float32) * g[..., None] * 0.18
        dots = np.zeros((FH, FW), np.float32)
        for y in range(14, FH, 26):
            for x in range(14, FW, 26):
                cv2.circle(dots, (x, y), 1, 1.0, -1, lineType=cv2.LINE_AA)
        bg = bg * (1 - dots[..., None] * 0.10) + np.array(G500, np.float32) * dots[..., None] * 0.10
        self.final_bg = bg / 255
        self.fade = np.clip((FH * 0.97 - yy) / (FH * 0.14), 0, 1)
        self.centers = self.person_centers()
        self.wave = self.waveform()

    # ---- footage ---------------------------------------------------------------
    def raw(self, i):
        return Image.open(os.path.join(self.work, "raw", f"{min(max(i, 1), N):04d}.jpg")).convert("RGB")

    def mask(self, i):
        return Image.open(os.path.join(self.work, "mask", f"{min(max(i, 1), N):04d}.png")).convert("L")

    def person_centers(self):
        xs = []
        for i in range(1, N + 1):
            m = np.asarray(self.mask(i)).astype(np.float32)
            col = m.sum(0)
            xs.append(float((col * np.arange(col.size)).sum() / (col.sum() + 1e-6)) if col.sum() > 0 else 540.0)
        xs = np.array(xs)
        out = xs.copy()
        cuts = [0, int(3.13 * FPS), int(8.77 * FPS), N]
        for a, b in zip(cuts[:-1], cuts[1:]):
            out[a:b] = np.median(xs[a:b])           # steady framing within each shot
        return out

    def waveform(self):
        import soundfile as sf
        v, sr = sf.read(os.path.join(self.work, "voice.wav"), dtype="float32")
        v = v.mean(1) if v.ndim > 1 else v
        n = 400
        seg = len(v) // n
        return np.array([np.abs(v[k * seg:(k + 1) * seg]).max() for k in range(n)])

    # ---- page --------------------------------------------------------------------
    def build_page(self):
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        page = np.array((246, 245, 241), np.float32) * np.ones((H, W, 1), np.float32)
        for cx, cy, r, a in ((980, 60, 520, 0.16), (60, 1880, 560, 0.12)):
            g = np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * r * r)))[..., None] * a
            page = page * (1 - g) + np.array(LIME, np.float32) * g
        img = Image.fromarray(page.astype(np.uint8)).convert("RGBA")
        d = ImageDraw.Draw(img)
        wm = Image.open(os.path.join(b1.ROOT, "brand", "logos", "ave-wordmark-black.png")).convert("RGBA")
        wm = wm.resize((int(wm.width * 44 / wm.height), 44), Image.LANCZOS)
        img.alpha_composite(wm, (85, 120))
        lab = txt("SAAS-STYLE TALKING HEAD", "mono", 22, G500, track=4)
        img.alpha_composite(lab, (W - 85 - lab.width, 132))
        # cards (frosted panels)
        for (x, y, w, h), fill in ((FINAL, (234, 233, 228)), (RAWC, (234, 233, 228)), (SCRIPT, (238, 237, 232)), (TIMEL, (28, 27, 25))):
            sh, p = soft_shadow(w, h, RAD, 26, 0.16, 16)
            img.alpha_composite(sh, (x - p, y - p))
            body = Image.new("RGBA", (w, h), fill + (255,)); body.putalpha(rmask(w, h, RAD))
            img.alpha_composite(body, (x, y))
            if fill != (28, 27, 25):
                d.rounded_rectangle((x, y, x + w - 1, y + h - 1), RAD, outline=(255, 255, 255, 255), width=2)
        # footer
        fy = 1640
        a = txt("DM", "xb", 70, INK)
        b = txt("“SAMPLE”", "xb", 70, INK)
        gap = 20
        tw = a.width + gap + b.width + 28
        x = (W - tw) / 2
        d.rounded_rectangle((x + a.width + gap - 4, fy - 6, x + tw + 4, fy + b.height + 4), 14, fill=LIME + (255,))
        img.alpha_composite(a, (int(x), fy))
        img.alpha_composite(b, (int(x + a.width + gap + 10), fy))
        s1 = txt("Get your first sample", "md", 38, G500)
        s2 = txt("edit.", "serif", 46, INK)
        tw2 = s1.width + 10 + s2.width
        img.alpha_composite(s1, (int((W - tw2) / 2), fy + 106))
        img.alpha_composite(s2, (int((W - tw2) / 2 + s1.width + 10), fy + 106 + s1.height - s2.height + 6))
        cr = txt("Original video: @braidenshaw", "md", 26, G500)
        img.alpha_composite(cr, ((W - cr.width) // 2, H - 90))
        self.chips = [(chip("Final video", LIME, INK), FINAL[0] - 22, FINAL[1] - 50),
                      (chip("Raw video", INK, PAPER), RAWC[0] - 14, RAWC[1] - 50),
                      (chip("Script", INK, PAPER), SCRIPT[0] - 14, SCRIPT[1] - 46),
                      (chip("Timeline", LIME, INK), TIMEL[0] - 22, TIMEL[1] - 48)]
        return img

    # ---- final video -----------------------------------------------------------------
    def person(self, i, t):
        """Crop his figure into the tall card on the clean background."""
        k = 1.0
        for t0, amt in ((1.30, .05), (4.90, .06), (6.72, .05), (10.24, .07), (13.92, .04), (15.98, .06)):
            d = t - t0
            if 0 <= d < 1.4:
                k += amt * expo(d / 0.15) * (1 - 0.6 * smooth((d - 0.2) / 1.1))
        ch = 608 / k
        cw = ch * 0.92
        cx = self.centers[min(i - 1, N - 1)]
        x0 = min(max(cx - cw / 2, 0), 1080 - cw)
        y0 = (608 - ch) * 0.3
        box = (x0, y0, x0 + cw, y0 + ch)
        ph = int(FW * ch / cw)
        src = np.asarray(self.raw(i).resize((FW, ph), Image.BICUBIC, box=box)).astype(np.float32) / 255
        ms = np.asarray(self.mask(i).resize((FW, ph), Image.BILINEAR, box=box)).astype(np.float32) / 255
        top = FH - ph + 30
        img = np.zeros((FH, FW, 3), np.float32); m = np.zeros((FH, FW), np.float32)
        y_a, s_a = max(top, 0), max(-top, 0)
        n_ = min(FH - y_a, ph - s_a)
        img[y_a:y_a + n_] = src[s_a:s_a + n_]; m[y_a:y_a + n_] = ms[s_a:s_a + n_]
        m = cv2.GaussianBlur(np.clip((m - 0.1) / 0.8, 0, 1), (0, 0), 1.0) * self.fade
        # clean, bright grade for the light set
        img = np.clip(img * 1.12 + 0.03, 0, 1)
        lum = img.mean(2, keepdims=True); img = lum + (img - lum) * 1.05
        return img, m

    def behind(self, t):
        """Big words that sit behind him."""
        lay = Image.new("RGBA", (FW, FH), (0, 0, 0, 0))
        items = [(1.30, 3.04, "Happiness", "xb", INK, True),
                 (13.92, 15.40, "normal.", "serif", G500, False), (15.98, END, "happiness", "serif", INK, True)]
        for on, off, s, kind, col, bar in items:
            if not (on <= t < off):
                continue
            p = spring(t - on, 11, 0.7)
            ex = smooth((off - t) / 0.18) if off < END else 1
            im = txt(s, kind, 150 if kind == "xb" else 170, col)
            if im.width > FW - 40:
                im = im.resize((FW - 40, int(im.height * (FW - 40) / im.width)), Image.LANCZOS)
            y = 150
            if bar:
                bw = im.width * expo((t - on - 0.15) / 0.5)
                ImageDraw.Draw(lay).rounded_rectangle(((FW - im.width) / 2, y + im.height - 36, (FW - im.width) / 2 + bw,
                                                       y + im.height - 6), 8, fill=LIME + (int(255 * ex),))
            place(lay, im, FW / 2, y + (1 - min(p, 1)) * 40, alpha=min(1, p * 1.5) * ex, scale=0.92 + 0.08 * min(p, 1.1),
                  blur=(1 - clamp01(p)) * 6, anchor="ct")
        return lay

    def front(self, t):
        """UI cards in front of him, acting out the script."""
        lay = Image.new("RGBA", (FW, FH), (0, 0, 0, 0))

        def show(im, x, y, on, off, anchor="c", rise=40):
            p = spring(t - on, 12, 0.72)
            ex = smooth((off - t) / 0.2) if off < END else 1
            if p > 0.01 and ex > 0.01:
                place(lay, im, x, y + (1 - min(p, 1)) * rise - (1 - ex) * 20, alpha=min(1, p * 1.5) * ex,
                      scale=(0.9 + 0.1 * min(p, 1.08)) * (0.96 + 0.04 * ex), blur=(1 - clamp01(p)) * 5, anchor=anchor)

        # 0 - 1.3  "Money can buy" pill
        if t < 3.04:
            words = [(0.0, "Money"), (0.58, "can"), (1.04, "buy")]
            s = " ".join(w for st, w in words if t >= st)
            pill = txt(s, "sb", 34, PAPER)
            pw = pill.width + 48
            pi = Image.new("RGBA", (pw, 64), (0, 0, 0, 0))
            ImageDraw.Draw(pi).rounded_rectangle((0, 0, pw - 1, 63), 32, fill=INK + (255,))
            pi.alpha_composite(pill, (24, (64 - pill.height) // 2))
            show(pi, FW / 2, 96, 0.0, 3.04)
        # 1.82 - 3.04  toggle
        if 1.82 <= t < 3.2:
            show(ui_toggle(clamp01(spring(t - 2.30, 16, 0.6))), FW * 0.5, FH * 0.40, 1.82, 3.04)
        # 3.54 - 4.4  "most of us" avatars
        if 3.40 <= t < 4.5:
            for k in range(4):
                show(avatar(k), FW / 2 - 66 + k * 44, 120, 3.54 + k * 0.06, 4.40)
        # 4.22 - 6.44  balance card, then a spend list
        if 4.22 <= t < 5.6:
            val = 4200 * smooth((t - 4.4) / 0.55)
            show(ui_balance(val, spark=(t - 4.3) / 0.8), FW / 2, FH * 0.22, 4.22, 5.50)
        if 5.42 <= t < 6.5:
            items = [("bag", "Bags", "-$640"), ("watch", "Watch", "-$720"), ("shoe", "Sneakers", "-$290")]
            show(ui_list(items, (t - 5.62) * 4.5), FW / 2, FH * 0.24, 5.42, 6.44)
        # 6.48 - 8.42  search "how to buy happiness"
        if 6.48 <= t < 8.5:
            q = "how to buy happiness"
            n = int(len(q) * clamp01((t - 6.6) / 1.1))
            res = clamp01((t - 7.9) / 0.3)
            show(ui_search(q[:n], int(t * 3) % 2 == 0 and res == 0, res), FW / 2, FH * 0.26, 6.48, 8.42)
        # 8.42 - 10.54  balance up, upgrade button with cursor
        if 8.42 <= t < 10.6:
            val = 4200 + 3600 * smooth((t - 9.25) / 0.6)
            show(ui_balance(val, "+86%" if t > 9.6 else None, 1.0), FW * 0.30, FH * 0.28, 8.42, 10.54)
        if 9.86 <= t < 10.6:
            pressed = clamp01(1 - abs(t - 10.27) / 0.08)
            show(ui_button(pressed), FW * 0.66, FH * 0.40, 9.86, 10.54)
            cx = FW * 0.66 + 120 * (1 - expo((t - 9.95) / 0.32)) + 22
            cy = FH * 0.40 + 90 * (1 - expo((t - 9.95) / 0.32)) + 14
            if t >= 9.95:
                place(lay, glyph("cursor", 44), cx, cy, scale=1 - 0.12 * pressed)
        # 10.54 - 12.24  product cards
        for k, (st, key, label) in enumerate(((10.62, "car", "Car"), (11.20, "house", "House"), (11.86, "jetski", "Vacation"))):
            if st <= t < 14.42:
                x = FW / 2 + (k - 1) * 128
                y = FH * 0.30 + abs(k - 1) * 18
                im = ui_product(key, label, self.work)
                if t >= 12.6:   # cards settle, shrink and grey out: "feels normal"
                    g = smooth((t - 12.6) / 1.0)
                    im = im.copy()
                    arr = np.asarray(im).astype(np.float32)
                    lum = arr[..., :3].mean(2, keepdims=True)
                    arr[..., :3] = arr[..., :3] * (1 - g * 0.85) + lum * g * 0.85
                    im = Image.fromarray(arr.astype(np.uint8))
                    y -= 95 * g
                    x = FW / 2 + (k - 1) * (128 - 40 * g)
                    im = im.resize((int(im.width * (1 - 0.25 * g)), int(im.height * (1 - 0.25 * g))), Image.LANCZOS)
                pr = spring(t - st, 12, 0.6)
                ex = smooth((14.42 - t) / 0.25)
                if pr > 0.01:
                    place(lay, im, x, y + (1 - min(pr, 1)) * 60 - (1 - ex) * 20, alpha=min(1, pr * 1.6) * ex,
                          rot=(k - 1) * -6 * min(pr, 1), scale=0.9 + 0.1 * min(pr, 1.08), anchor="c")
        # 12.9 - end  happiness meter drains
        if 12.9 <= t:
            lvl = 1.0 - 0.72 * smooth((t - 13.1) / 1.2) - 0.28 * smooth((t - 15.2) / 0.8)
            show(ui_meter(max(lvl, 0)), FW / 2, FH * 0.385, 12.9, END + 1)
        return lay

    def captions(self, base, t):
        """Two-line karaoke captions at the bottom of the final card."""
        groups = [(0.0, 1.82), (1.82, 3.04), (3.04, 4.22), (4.22, 5.12), (5.12, 6.48), (6.48, 8.42), (8.42, 9.86),
                  (9.86, 10.54), (10.54, 12.24), (12.24, 13.62), (13.62, 14.42), (14.42, 15.44), (15.44, END + 1)]
        g = next(((a, b) for a, b in groups if a <= t < b), None)
        if not g:
            return
        ws = [(st, en, w) for st, en, w in self.words if g[0] - 0.01 <= st < g[1]]
        if not ws:
            return
        ims = [txt(w, "b", 34, INK) for _, _, w in ws]
        sp = 10
        lines, cur, cw = [], [], 0
        for item, im in zip(ws, ims):
            if cur and cw + im.width + sp > FW - 70:
                lines.append(cur); cur, cw = [], 0
            cur.append((item, im)); cw += im.width + sp
        lines.append(cur)
        y = FH - 60 - len(lines) * 50
        d = ImageDraw.Draw(base)
        for line in lines:
            tw = sum(im.width for _, im in line) + sp * (len(line) - 1)
            x = (FW - tw) / 2
            plate = Image.new("RGBA", (int(tw + 36), 50), (0, 0, 0, 0))
            ImageDraw.Draw(plate).rounded_rectangle((0, 0, plate.width - 1, 49), 16, fill=(255, 255, 255, 225))
            base.alpha_composite(plate, (int(x - 18), int(y - 6)))
            for (st, en, w), im in line:
                if t >= st - 0.02:
                    q = expo((t - st + 0.02) / 0.25)
                    active = st <= t < max(en, st + 0.12) + 0.05
                    if active:
                        d.rounded_rectangle((x - 6, y - 2, x + im.width + 6, y + im.height + 2), 10, fill=LIME + (255,))
                    place(base, im, x, y + (1 - q) * 10, alpha=q)
                else:
                    ghost = im.copy(); ghost.putalpha(ghost.getchannel("A").point(lambda v: int(v * 0.22)))
                    base.alpha_composite(ghost, (int(x), int(y)))
                x += im.width + sp
            y += 56

    def final_video(self, i, t):
        img, m = self.person(i, t)
        bg = self.final_bg.copy()
        # soft contact shadow under him
        sh = cv2.GaussianBlur(m, (0, 0), 18)
        sh = np.roll(sh, 14, axis=0) * 0.18
        bg = bg * (1 - sh[..., None])
        behind = np.asarray(self.behind(t)).astype(np.float32) / 255
        bg = bg * (1 - behind[..., 3:4]) + behind[..., :3] * behind[..., 3:4]
        a = bg * (1 - m[..., None]) + img * m[..., None]
        out = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).convert("RGBA")
        out.alpha_composite(self.front(t))
        self.captions(out, t)
        # a soft scale bump on each shot change
        for b in (3.13, 8.77):
            d = t - b
            if 0 <= d < 0.25:
                k = 1 + 0.05 * (1 - expo(d / 0.25))
                cw, ch = int(FW * k), int(FH * k)
                out = out.resize((cw, ch), Image.BICUBIC).crop(((cw - FW) // 2, (ch - FH) // 2, (cw - FW) // 2 + FW, (ch - FH) // 2 + FH))
        out.putalpha(self.final_mask)
        return out

    # ---- raw, script, timeline ------------------------------------------------------
    def raw_card(self, i):
        x, y, w, h = RAWC
        cx = self.centers[min(i - 1, N - 1)]
        cw = 608 * w / h
        x0 = min(max(cx - cw / 2, 0), 1080 - cw)
        im = self.raw(i).resize((w, h), Image.BICUBIC, box=(x0, 0, x0 + cw, 608)).convert("RGBA")
        im.putalpha(self.raw_mask)
        return im

    def script_card(self, t):
        x, y, w, h = SCRIPT
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        pad, lh = 34, 40
        top_pad = 56
        lines, cur, cw = [], [], 0
        sizes = [txt(wd, "md", 29, INK).width for _, _, wd in self.words]
        for k, sw in enumerate(sizes):
            if cur and cw + sw > w - 2 * pad:
                lines.append(cur); cur, cw = [], 0
            cur.append(k); cw += sw + 8
        lines.append(cur)
        cur_k = max([k for k, (st, _, _) in enumerate(self.words) if st <= t] or [0])
        cur_line = next(li for li, ln in enumerate(lines) if cur_k in ln)
        visible = (h - top_pad - pad) // lh
        first = min(max(0, cur_line - visible + 2), max(0, len(lines) - visible))
        for li in range(first, min(len(lines), first + visible)):
            yy = top_pad + (li - first) * lh
            xx = pad
            for k in lines[li]:
                st, en, wd = self.words[k]
                if k == cur_k and t >= st:
                    col = INK
                    tw = txt(wd, "md", 29, col)
                    d.rounded_rectangle((xx - 5, yy - 1, xx + tw.width + 5, yy + tw.height + 1), 8, fill=LIME + (255,))
                elif st <= t:
                    col = INK
                else:
                    col = (178, 175, 166)
                tw = txt(wd, "md", 29, col)
                im.alpha_composite(tw, (int(xx), int(yy)))
                xx += tw.width + 8
        return im

    def timeline_card(self, t):
        x, y, w, h = TIMEL
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        left, top, rowh = 186, 70, 40
        tracks = [("V5  Captions", PAPER), ("V4  UI cards", LIME), ("V3  Words", (230, 236, 200)), ("V2  Cut-out", OLIVE),
                  ("V1  Raw", G500), ("A1  Voice", (150, 190, 60)), ("A2  Music", (110, 110, 100)), ("A3  SFX", LIME)]
        # header: timecode + ruler
        tc = f"00:00:{int(t):02d}:{int((t % 1) * FPS):02d}"
        tci = txt(tc, "mono6", 24, LIME); im.alpha_composite(tci, (w - tci.width - 26, 16))
        span = w - left - 24
        X = lambda s: left + span * s / END
        for s in range(0, int(END) + 1):
            xx = X(s)
            d.line((xx, 54, xx, 62 if s % 5 else 66), fill=G500 + (255,), width=1)
            if s % 5 == 0:
                im.alpha_composite(txt(f"00:{s:02d}", "mono", 16, G500), (int(xx) + 4, 30))
        for r, (name, col) in enumerate(tracks):
            ty = top + r * rowh
            d.rectangle((0, ty, w, ty + rowh - 2), fill=(36, 35, 32, 255) if r % 2 else (32, 31, 28, 255))
            im.alpha_composite(txt(name, "mono", 17, (200, 198, 190)), (24, ty + 11))
        def clip(r, a, b, col, label=""):
            ty = top + r * rowh + 6
            d.rounded_rectangle((X(a), ty, max(X(a) + 3, X(b) - 2), ty + rowh - 14), 5, fill=col + (255,))
            if label and X(b) - X(a) > 60:
                lab = txt(label, "mono", 13, INK if sum(col) > 400 else PAPER)
                im.alpha_composite(lab.crop((0, 0, min(lab.width, int(X(b) - X(a) - 12)), lab.height)), (int(X(a)) + 6, ty + 5))
        caps = [(0.0, 1.82), (1.82, 3.04), (3.04, 4.22), (4.22, 5.12), (5.12, 6.48), (6.48, 8.42), (8.42, 9.86),
                (9.86, 10.54), (10.54, 12.24), (12.24, 13.62), (13.62, 14.42), (14.42, 15.44), (15.44, END)]
        for a, b in caps:
            clip(0, a, b, PAPER)
        for a, b, lab in ((0, 3.04, "pill"), (1.82, 3.04, "toggle"), (3.54, 4.4, "avatars"), (4.22, 6.44, "balance"),
                          (5.42, 6.44, "list"), (6.48, 8.42, "search"), (8.42, 10.54, "balance"), (9.86, 10.54, "button"),
                          (10.62, 14.42, "products"), (12.9, END, "meter")):
            clip(1, a, b, LIME, lab)
        for a, b, lab in ((1.30, 3.04, "Happiness"), (13.92, 15.4, "normal"), (15.98, END, "happiness")):
            clip(2, a, b, (230, 236, 200), lab)
        clip(3, 0, END, OLIVE, "braiden_cutout")
        for a, b, lab in ((0, 3.13, "braiden_wide.mp4"), (3.13, 8.77, "braiden_close.mp4"), (8.77, END, "braiden_wide.mp4")):
            clip(4, a, b, G500, lab)
        # voice waveform, music block, sfx markers
        ty = top + 5 * rowh + 20
        wv = self.wave / (self.wave.max() + 1e-6)
        for k, v in enumerate(wv):
            xx = X(END * k / len(wv))
            d.line((xx, ty - v * 13, xx, ty + v * 13), fill=(150, 190, 60, 255), width=1)
        clip(6, 0, END, (90, 90, 82), "timeless_instrumental.mp3")
        for t0, _ in b1.SFX:
            xx = X(t0)
            d.polygon([(xx, top + 7 * rowh + 8), (xx + 6, top + 7 * rowh + 18), (xx, top + 7 * rowh + 28), (xx - 6, top + 7 * rowh + 18)],
                      fill=LIME + (255,))
        # playhead
        px = X(t)
        d.line((px, 50, px, h - 10), fill=LIME + (255,), width=2)
        d.polygon([(px - 8, 44), (px + 8, 44), (px, 56)], fill=LIME + (255,))
        im.putalpha(Image.fromarray(np.minimum(np.asarray(im.getchannel("A")), np.asarray(rmask(w, h, RAD)))))
        return im

    def frame(self, fi):
        t = fi / FPS
        i = fi + 1
        page = self.page.copy()
        page.alpha_composite(self.final_video(i, t), (FINAL[0], FINAL[1]))
        page.alpha_composite(self.raw_card(i), (RAWC[0], RAWC[1]))
        page.alpha_composite(self.script_card(t), (SCRIPT[0], SCRIPT[1]))
        page.alpha_composite(self.timeline_card(t), (TIMEL[0], TIMEL[1]))
        for c, x, y in self.chips:
            page.alpha_composite(c, (x, y))
        return np.asarray(page.convert("RGB"))


SFX = ([(t, "bloop") for t in (0.0, 1.82, 3.54, 4.22, 5.42, 6.48, 9.86, 10.62, 11.20, 11.86, 12.9)]
       + [(t, "thock") for t in (1.30, 4.90, 10.27, 15.98)]
       + [(t, "ding") for t in (2.30, 7.90, 9.6)]
       + [(t, "whoosh") for t in (3.13, 8.77, 13.92)])
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
            Image.fromarray(R.frame(fi)).save(os.path.join(work, f"saas_{fi:04d}.png"))
        return
    vid = os.path.join(work, "video_saas.mp4")
    p = subprocess.Popen(f'ffmpeg -v error -y -f rawvideo -pix_fmt rgb24 -s {W}x{H} -r {FPS} -i - '
                         f'-c:v libx264 -preset slow -crf 15 -pix_fmt yuv420p "{vid}"', shell=True, stdin=subprocess.PIPE)
    with Pool(3, initializer=_init, initargs=(work,)) as pool:
        for buf in pool.imap(_frame, range(N), chunksize=3):
            p.stdin.write(buf)
    p.stdin.close(); p.wait()
    mix, master = os.path.join(work, "mix_saas.wav"), os.path.join(work, "master_saas.wav")
    b1.build_audio(work, mix, music, start)
    v1.loudnorm(mix, master)
    out = os.path.join(work, "AVE_Braiden_SaaS_Breakdown.mp4")
    v1.sh(f'ffmpeg -v error -y -i "{vid}" -i "{master}" -c:v copy -c:a aac -b:a 256k -shortest -movflags +faststart "{out}"')
    print(out)


if __name__ == "__main__":
    cmd, src, work = sys.argv[1:4]
    if cmd == "render":
        render(work, sys.argv[4] if len(sys.argv) > 4 else None, float(sys.argv[5]) if len(sys.argv) > 5 else 0.0)
    elif cmd == "stills":
        render(work, only=[int(round(float(x) * FPS)) for x in sys.argv[4:]])
