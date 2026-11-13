"""AVE Studio · Before / After reel, V2: follows the reference reel's design
closely (layout, type treatment, cards, pills, bubbles, timing) and swaps its
purple palette for AVE's colours (lime #C8FF2E, ink #0E0E0E, off-white #F3F2EE).

All graphics are drawn here; only the creator's raw footage and voice come
from the reference (see build.py for the prep of the voice stem + transcript).

Usage:
    python build_v2.py prep   REF.mp4 WORK_DIR
    python build_v2.py render REF.mp4 WORK_DIR      # -> WORK_DIR/AVE_Before_After_V2.mp4
    python build_v2.py stills REF.mp4 WORK_DIR 1.0 7.5 ...
"""
import math, os, subprocess, sys, urllib.request
from functools import lru_cache

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

import build as v1
from build import ease_out, back_out, paste, rounded_mask, fit, sh

W, H, FPS = 1080, 1920, 30
END = 1355 / FPS

INK = (14, 14, 14)
PAPER = (243, 242, 238)
WHITE = (255, 255, 255)
LIME = np.array((200, 255, 46), np.float32)
LIMEt = (200, 255, 46)
LIME_PALE = (226, 246, 176)      # lavender of the reference -> pale lime
LIME_DEEP = (122, 160, 10)       # deep purple of the reference -> deep lime
OLIVE = (70, 92, 6)
GREY = (85, 87, 74)

CARD = (425, 435, 540, 960)
BEFORE = (117, 537, 330, 772)
RADIUS = 18

# footage placement inside the After card: wider framing, like the reference
SRC_W, SRC_H = 448, 1049
SRC_X, SRC_Y = CARD[2] - SRC_W, -20

FONT_URLS = {
    "LeagueGothic.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/leaguegothic/LeagueGothic%5Bwdth%5D.ttf",
    "Urbanist.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/urbanist/Urbanist%5Bwght%5D.ttf",
    "Anton.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/anton/Anton-Regular.ttf",
}
INTER = os.path.join(v1.FONTS, "InterDisplay-Medium.otf")

# ---- timeline -----------------------------------------------------------------
SEGMENTS = v1.SEGMENTS
NUM_CARDS = {1: (6.10, ("lack of", 6.62), ("DIRECTION", 7.00), "flag"),
             2: (20.58, ("bad", 21.12), ("DESIGN", 21.36), "palette"),
             3: (31.14, ("poor", 31.72), ("POST-PRODUCTION", 31.94), "clap")}
BIG = [  # (on, off, lines, kicker, kicker align, icon)
    (0.62, 2.76, ["EDITS"], "IF YOU LOOK AT YOUR", "c", "magnifier"),
    (3.50, 5.87, ["INSTAGRAM"], "WHAT I SEE ON", "l", "camera"),
    (8.96, 11.50, ["YOU NEED TO KNOW", "EXACTLY"], None, "c", "bulb"),
    (17.90, 20.47, ["YOU GONNA", "GET LOST"], None, "c", "pin"),
    (22.14, 24.87, ["DESIGN"], None, "c", "palette"),
    (29.24, 30.47, ["BEGINNER"], "YOU ARE A", "c", "laptop"),
    (33.02, 35.42, ["PRODUCTION"], "POST", "c", "clap"),
    (35.52, 36.90, ["NEED TO LOOK"], "YOU", "c", "eyes"),
    (41.94, END, ["REMEMBER"], "JUST MAKE SURE TO", "c", "brain"),
]
KICK_ONLY = [(0.0, 0.62, "IF YOU LOOK AT YOUR"), (2.76, 3.50, "WHAT I SEE ON"),
             (41.20, 41.94, "JUST MAKE SURE TO")]
CAPS = [  # (small on, big on, off, small, big)
    (1.14, 1.76, 2.76, "you   think", "THAT LOOKS NOTHING"),
    (4.10, None, 5.87, "its probably", None),
    (7.62, 7.94, 8.96, "to create", "A GOOD EDIT"),
    (9.74, 10.36, 11.50, "what you want", "YOUR SCENE TO LOOK LIKE"),
    (18.84, 19.18, 20.47, "and your edit", "IS NOT GONNA LOOK THAT GOOD"),
    (None, 22.42, 24.87, None, "IS THE MOST IMPORTANT SKILL"),
    (33.64, 33.84, 35.42, "is what", "BRINGS YOUR ANIMATIONS TO LIFE"),
    (42.96, 44.02, END, "the next time your edit", "LOOKS BORING"),
]
CHECKS = [(25.26, "Imbalanced scenes."), (26.46, "Bad contrast."), (27.26, "Uncommon patterns.")]
CHECKS_OFF = 30.47
BUBBLES = [(5.36, 5.87), (42.50, 44.00)]
FX_ROWS = [(37.06, "Vignette", "vignette"), (37.76, "Blur", "drop"),
           (38.46, "Chromatic Aberration", "aperture"), (39.62, "Noise", "speaker"),
           (40.30, "Posterize Time", "hourglass")]
INSP = dict(vault=12.20, house=13.70, book=14.22, refs=14.80)
SFX = v1.SFX


# ===========================================================================
def fonts_dir(work):
    d = os.path.join(work, "fonts")
    os.makedirs(d, exist_ok=True)
    for name, url in FONT_URLS.items():
        p = os.path.join(d, name)
        if not os.path.exists(p):
            urllib.request.urlretrieve(url, p)
    return d


FD = None


@lru_cache(None)
def font(kind, size):
    if kind == "gothic":      # ultra-condensed display
        f = ImageFont.truetype(os.path.join(FD, "LeagueGothic.ttf"), size)
        f.set_variation_by_axes([75]); return f
    if kind == "gothicw":
        f = ImageFont.truetype(os.path.join(FD, "LeagueGothic.ttf"), size)
        f.set_variation_by_axes([100]); return f
    if kind.startswith("urb"):  # urb400, urb800 ...
        f = ImageFont.truetype(os.path.join(FD, "Urbanist.ttf"), size)
        f.set_variation_by_axes([int(kind[3:])]); return f
    if kind == "anton":
        return ImageFont.truetype(os.path.join(FD, "Anton.ttf"), size)
    if kind == "inter":
        return ImageFont.truetype(INTER, size)
    raise ValueError(kind)


@lru_cache(None)
def txt(s, kind, size, color, alpha=255):
    f = font(kind, size)
    l, t, r, b = f.getbbox(s)
    im = Image.new("RGBA", (r - l + 8, b - t + 8), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((4 - l, 4 - t), s, font=f, fill=tuple(color) + (alpha,))
    return im.crop(im.getbbox() or (0, 0, 1, 1))


def vgrad(im, top, bottom, a_top=1.0, a_bot=1.0, mid=None):
    """Recolour a text image with a vertical gradient."""
    a = np.asarray(im.getchannel("A")).astype(np.float32) / 255
    h = a.shape[0]
    y = np.linspace(0, 1, h)[:, None, None]
    top, bottom = np.array(top, np.float32), np.array(bottom, np.float32)
    if mid is not None:
        mc, mp = np.array(mid[0], np.float32), mid[1]
        col = np.where(y < mp, top + (mc - top) * (y / mp), mc + (bottom - mc) * ((y - mp) / (1 - mp)))
    else:
        col = top + (bottom - top) * y
    al = (a_top + (a_bot - a_top) * y[..., 0]) * a
    out = np.dstack([np.broadcast_to(col, (h, a.shape[1], 3)), al[..., None] * 255])
    return Image.fromarray(out.clip(0, 255).astype(np.uint8), "RGBA")


def hgrad(im, left, right):
    a = np.asarray(im.getchannel("A")).astype(np.float32)
    w = a.shape[1]
    x = np.linspace(0, 1, w)[None, :, None]
    col = np.array(left, np.float32) + (np.array(right, np.float32) - np.array(left, np.float32)) * x
    out = np.dstack([np.broadcast_to(col, a.shape + (3,)), a[..., None]])
    return Image.fromarray(out.clip(0, 255).astype(np.uint8), "RGBA")


def long_shadow(im, length=110, a=0.10):
    al = im.getchannel("A")
    acc = Image.new("L", (im.width + length, im.height + length), 0)
    for k in range(0, length, 2):
        lay = Image.new("L", acc.size, 0)
        lay.paste(al.point(lambda v, k=k: int(v * a * (1 - k / length))), (k, k))
        acc = Image.fromarray(np.maximum(np.asarray(acc), np.asarray(lay)))
    acc = acc.filter(ImageFilter.GaussianBlur(3))
    sh_ = Image.new("RGBA", acc.size, (60, 64, 40, 0))
    sh_.putalpha(acc)
    return sh_


# ---- sticker icons (our own drawings) -----------------------------------------
@lru_cache(None)
def sticker(kind, size):
    S = size * 4
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    lw = S // 16
    L, K, Wt = LIMEt + (255,), INK + (255,), WHITE + (255,)
    m = S / 2
    def E(cx, cy, r, **k): d.ellipse((cx - r, cy - r, cx + r, cy + r), **k)
    if kind == "magnifier":
        d.line((m + S * .1, m + S * .1, S * .88, S * .88), fill=K, width=lw * 3)
        E(m - S * .08, m - S * .08, S * .3, fill=(235, 255, 200, 230), outline=K, width=lw)
    elif kind == "camera":
        d.rounded_rectangle((S * .12, S * .12, S * .88, S * .88), S * .22, fill=L, outline=K, width=lw)
        E(m, m, S * .17, outline=K, width=lw)
        E(S * .7, S * .3, S * .045, fill=K)
    elif kind == "bulb":
        E(m, S * .4, S * .28, fill=L, outline=K, width=lw)
        d.rectangle((m - S * .13, S * .62, m + S * .13, S * .82), fill=GREY + (255,), outline=K, width=lw)
        d.line((m - S * .07, S * .3, m, S * .45, m + S * .07, S * .3), fill=K, width=lw // 2 + 2)
    elif kind == "pin":
        d.line((m, m, S * .22, S * .9), fill=K, width=lw)
        E(m + S * .08, S * .32, S * .22, fill=L, outline=K, width=lw)
        d.polygon([(S * .3, S * .52), (S * .62, S * .5), (S * .5, S * .62)], fill=L, outline=K)
    elif kind == "palette":
        E(m, m, S * .38, fill=PAPER + (255,), outline=K, width=lw)
        for (x, y) in ((.36, .38), (.55, .3), (.68, .48), (.38, .6)):
            E(S * x, S * y, S * .07, fill=L if x != .55 else K, outline=K, width=lw // 2)
        E(S * .6, S * .68, S * .08, fill=(0, 0, 0, 0), outline=K, width=lw // 2)
    elif kind == "laptop":
        d.rounded_rectangle((S * .18, S * .2, S * .82, S * .62), S * .04, fill=GREY + (255,), outline=K, width=lw)
        d.rectangle((S * .24, S * .26, S * .76, S * .56), fill=L)
        d.polygon([(S * .08, S * .66), (S * .92, S * .66), (S * .84, S * .78), (S * .16, S * .78)], fill=PAPER + (255,), outline=K)
    elif kind == "clap":
        d.rectangle((S * .14, S * .42, S * .86, S * .84), fill=INK + (255,))
        d.polygon([(S * .14, S * .22), (S * .84, S * .1), (S * .88, S * .3), (S * .17, S * .4)], fill=K)
        for k in range(4):
            x = S * (.22 + k * .16)
            d.polygon([(x, S * .2 - k * S * .02), (x + S * .07, S * .19 - k * S * .02),
                       (x + S * .02, S * .37 - k * S * .02), (x - S * .05, S * .38 - k * S * .02)], fill=Wt)
            d.rectangle((x - S * .04, S * .42, x + S * .04, S * .52), fill=L)
    elif kind == "eyes":
        for cx in (.32, .68):
            d.ellipse((S * (cx - .16), S * .26, S * (cx + .16), S * .74), fill=Wt, outline=K, width=lw)
            E(S * (cx + .05), S * .52, S * .07, fill=K)
    elif kind == "brain":
        for (x, y, r) in ((.38, .4, .2), (.62, .4, .2), (.34, .6, .18), (.66, .6, .18), (.5, .32, .18)):
            E(S * x, S * y, S * r, fill=L, outline=K, width=lw)
        for (x, y, r) in ((.38, .4, .2), (.62, .4, .2), (.34, .6, .18), (.66, .6, .18), (.5, .32, .18)):
            E(S * x, S * y, S * r - lw, fill=L)
        d.line((m, S * .22, m, S * .78), fill=K, width=lw)
        d.arc((S * .25, S * .35, S * .45, S * .55), 200, 340, fill=K, width=lw // 2 + 2)
        d.arc((S * .55, S * .45, S * .75, S * .65), 200, 340, fill=K, width=lw // 2 + 2)
    elif kind == "flag":
        d.line((S * .3, S * .15, S * .3, S * .88), fill=Wt, width=lw)
        d.polygon([(S * .3, S * .15), (S * .78, S * .3), (S * .3, S * .48)], fill=Wt)
    # soft drop shadow
    al = im.getchannel("A").filter(ImageFilter.GaussianBlur(S * .03))
    sh_ = Image.new("RGBA", im.size, (0, 0, 0, 0))
    sh_.putalpha(al.point(lambda v: int(v * .45)))
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    out.alpha_composite(sh_, (0, S // 30))
    out.alpha_composite(im)
    return out.resize((size, size), Image.LANCZOS)


@lru_cache(None)
def glyph(kind, size, color):
    """Small line glyphs for the effect list and title tiles."""
    S = size * 4
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = tuple(color) + (255,)
    lw = max(4, S // 12)
    if kind == "vignette":
        d.rounded_rectangle((S * .12, S * .12, S * .88, S * .88), S * .12, outline=c, width=lw)
        d.ellipse((S * .3, S * .3, S * .7, S * .7), outline=c, width=lw)
    elif kind == "drop":
        d.polygon([(S * .5, S * .08), (S * .78, S * .55), (S * .22, S * .55)], fill=c)
        d.ellipse((S * .22, S * .32, S * .78, S * .9), fill=c)
    elif kind == "aperture":
        d.ellipse((S * .1, S * .1, S * .9, S * .9), outline=c, width=lw)
        for k in range(6):
            a = k * math.pi / 3
            d.line((S * .5 + S * .38 * math.cos(a), S * .5 + S * .38 * math.sin(a),
                    S * .5 + S * .2 * math.cos(a + 1.2), S * .5 + S * .2 * math.sin(a + 1.2)), fill=c, width=lw)
    elif kind == "speaker":
        d.polygon([(S * .1, S * .35), (S * .3, S * .35), (S * .55, S * .12), (S * .55, S * .88), (S * .3, S * .65), (S * .1, S * .65)], fill=c)
        for k in range(3):
            d.line((S * .68, S * (.3 + k * .2), S * .9, S * (.25 + k * .25)), fill=c, width=lw // 2 + 2)
    elif kind == "hourglass":
        d.polygon([(S * .2, S * .1), (S * .8, S * .1), (S * .5, S * .5)], fill=c)
        d.polygon([(S * .5, S * .5), (S * .8, S * .9), (S * .2, S * .9)], fill=c)
    elif kind in ("flag", "palette", "clap"):
        return sticker(kind if kind != "clap" else "clap", size)
    return im.resize((size, size), Image.LANCZOS)


# ===========================================================================
def build_page():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    pale = np.array(LIME_PALE, np.float32); white = np.array((250, 252, 244), np.float32)
    # diagonal light sweeps, like the reference's page
    s = (xx * 0.55 + yy * 0.45) / (W * 0.55 + H * 0.45)
    band = 0.5 + 0.5 * np.cos((s * 2.4 + 0.15) * math.pi)
    band = band ** 1.4
    page = pale * (1 - band[..., None]) + white * band[..., None]
    img = Image.fromarray(page.clip(0, 255).astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(img)

    # top line: badge + label
    lab = txt("EDITED BY AVE STUDIO.", "urb600", 38, INK)
    bw, bh = 62, 46
    tot = bw + 14 + lab.width
    x0, y0 = (W - tot) / 2, 262
    d.rounded_rectangle((x0, y0, x0 + bw, y0 + bh), 9, fill=INK + (255,))
    wm = Image.open(os.path.join(v1.ROOT, "brand", "logos", "ave-wordmark-lime.png")).convert("RGBA")
    wm = fit(wm, bw - 14, bh - 18)
    paste(img, wm, x0 + bw / 2, y0 + bh / 2, anchor="c")
    paste(img, lab, x0 + bw + 14, y0 + (bh - lab.height) / 2)

    def chip(x, y, w, label, fill, a):
        h = 48
        lay = Image.new("RGBA", (w + 4, h + 4), (0, 0, 0, 0))
        dl = ImageDraw.Draw(lay)
        dl.rounded_rectangle((1, 1, w, h), 12, fill=fill + (a,), outline=(255, 255, 255, 200), width=2)
        dl.ellipse((16, h / 2 - 12, 40, h / 2 + 12), outline=INK + (255,), width=3)
        t = txt(label, "urb500", 34, INK)
        lay.alpha_composite(t, (54, int((h - t.height) / 2)))
        img.alpha_composite(lay, (int(x), int(y)))
    chip(CARD[0], CARD[1] - 70, 288, "After", LIMEt, 255)
    chip(BEFORE[0] + 3, BEFORE[1] - 72, 286, "Before", LIMEt, 150)

    # CTA
    a = txt("Comment", "urb500", 72, GREY)
    b = txt("“SAMPLE”", "urb900", 72, INK)
    gap = 18
    x = (W - a.width - gap - b.width) / 2
    y = 1490
    paste(img, a, x, y + b.height - a.height)
    paste(img, b, x + a.width + gap, y)
    s2 = txt("and i'll send you the project file.", "urb500", 46, GREY)
    paste(img, s2, W / 2, 1580, anchor="ct")
    return img


def shadow_layer(box, r=RADIUS, oy=18, blur=46, a=0.22, pad=100):
    x, y, w, h = box
    m = Image.new("L", (w + 2 * pad, h + 2 * pad), 0)
    m.paste(rounded_mask(w, h, r), (pad, pad + oy))
    m = m.filter(ImageFilter.GaussianBlur(blur / 2))
    lay = Image.new("RGBA", m.size, (40, 52, 10, 0))
    lay.putalpha(m.point(lambda v: int(v * a)))
    return lay, (x - pad, y - pad)


def vignette_card():
    """White centre, lime edges (reference: white centre, purple edges)."""
    w, h = CARD[2], CARD[3]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((xx - w / 2) / (w * 0.72)) ** 2 + ((yy - h / 2) / (h * 0.50)) ** 2)
    v = np.clip((d - 0.62) / 0.5, 0, 1) ** 1.2
    col = np.array(WHITE, np.float32) * (1 - v[..., None]) + LIME * v[..., None]
    return Image.fromarray(col.astype(np.uint8)).convert("RGBA")


def soft_card(arcs=True, plus=False):
    w, h = CARD[2], CARD[3]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    s = (xx / w * 0.6 + yy / h * 0.4)
    band = (0.5 + 0.5 * np.cos((s * 2.0 + 0.2) * math.pi)) ** 1.2
    col = np.array(LIME_PALE, np.float32) * (1 - band[..., None]) + np.array((252, 253, 248), np.float32) * band[..., None]
    img = Image.fromarray(col.astype(np.uint8)).convert("RGBA")
    if arcs:
        lay = Image.new("RGBA", (w * 2, h * 2), (0, 0, 0, 0))
        dl = ImageDraw.Draw(lay)
        for box in ((-w * 1.1, h * 0.3, w * 1.7, h * 3.0), (w * 0.9, -h * 1.0, w * 4.0, h * 1.9)):
            dl.ellipse(tuple(v * 2 for v in box), outline=(110, 130, 40, 70), width=3)
        img.alpha_composite(lay.resize((w, h), Image.LANCZOS))
    if plus:
        for (cx, cy, r) in ((40, 30, 70), (w - 50, h - 80, 64)):
            p = Image.new("RGBA", (r * 3, r * 3), (0, 0, 0, 0))
            dp = ImageDraw.Draw(p)
            c = r * 1.5
            dp.rounded_rectangle((c - r, c - r * 0.36, c + r, c + r * 0.36), r * 0.3, fill=LIMEt + (255,))
            dp.rounded_rectangle((c - r * 0.36, c - r, c + r * 0.36, c + r), r * 0.3, fill=LIMEt + (255,))
            p = p.rotate(20, resample=Image.BICUBIC).filter(ImageFilter.GaussianBlur(5))
            img.alpha_composite(p, (int(cx - c), int(cy - c)))
    return img


# ---- 3D-ish props for the inspiration card (our own drawings) ----------------------
@lru_cache(None)
def prop_vault(size):
    S = size * 3
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    front = [(S * .18, S * .30), (S * .70, S * .18), (S * .76, S * .80), (S * .26, S * .92)]
    side = [(S * .70, S * .18), (S * .90, S * .30), (S * .94, S * .86), (S * .76, S * .80)]
    top = [(S * .18, S * .30), (S * .40, S * .12), (S * .90, S * .30), (S * .70, S * .18)]
    d.polygon(top, fill=(230, 255, 150, 255))
    d.polygon(side, fill=LIME_DEEP + (255,))
    d.polygon(front, fill=LIMEt + (255,))
    d.polygon([(S * .27, S * .38), (S * .63, S * .30), (S * .68, S * .74), (S * .33, S * .82)], outline=(150, 190, 20, 255), width=S // 90)
    d.ellipse((S * .40, S * .48, S * .52, S * .60), fill=WHITE + (255,), outline=LIME_DEEP + (255,), width=S // 120)
    for k in range(10):
        a = k * math.pi / 5
        d.line((S * .46 + S * .08 * math.cos(a), S * .54 + S * .08 * math.sin(a),
                S * .46 + S * .1 * math.cos(a), S * .54 + S * .1 * math.sin(a)), fill=LIME_DEEP + (255,), width=S // 150)
    for y in (.36, .62):
        d.rounded_rectangle((S * .64, S * y, S * .75, S * (y + .1)), S * .02, fill=(245, 248, 235, 255))
    return im.resize((size, size), Image.LANCZOS)


@lru_cache(None)
def prop_book(size):
    S = size * 3
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.polygon([(S * .30, S * .14), (S * .80, S * .06), (S * .86, S * .82), (S * .36, S * .94)], fill=(250, 250, 244, 255))
    d.polygon([(S * .24, S * .16), (S * .30, S * .14), (S * .36, S * .94), (S * .28, S * .96)], fill=LIME_DEEP + (255,))
    d.polygon([(S * .34, S * .12), (S * .86, S * .02), (S * .92, S * .80), (S * .40, S * .90)], fill=LIMEt + (255,))
    d.line((S * .62, S * .07, S * .66, S * .40), fill=LIME_DEEP + (255,), width=S // 40)
    return im.resize((size, size), Image.LANCZOS)


# ===========================================================================
class Renderer:
    def __init__(self, work):
        global FD
        FD = fonts_dir(work)
        self.work = work
        self.page = build_page()
        bs, bp = shadow_layer(BEFORE, a=0.16)
        self.page.alpha_composite(bs, bp)
        self.card_mask = rounded_mask(CARD[2], CARD[3], RADIUS)
        self.prior = cv2.imread(os.path.join(work, "mask_prior.png"), cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255
        self.before_mask = rounded_mask(BEFORE[2], BEFORE[3], RADIUS)
        self.card_shadow = shadow_layer(CARD)
        self.vig = vignette_card()
        self.soft = soft_card()
        self.soft_plus = soft_card(plus=True)
        h = CARD[3]
        y = np.linspace(0, 1, h)[:, None]
        # backdrop light: dark ceiling, lime-lit wall, dark desk (the reference's purple room)
        self.wall = (np.clip((y - 0.04) / 0.30, 0, 1) * np.clip((0.93 - y) / 0.25, 0, 1))[..., None]

    def gray(self, d, i):
        i = min(max(i, 1), 1355)
        return cv2.imread(os.path.join(self.work, d, f"{i:04d}.png"), cv2.IMREAD_GRAYSCALE)

    # ---- speaker card ------------------------------------------------------
    def speaker(self, i, t, seg):
        w, h = CARD[2], CARD[3]
        g = self.gray("after2", i).astype(np.float32) / 255
        m = np.maximum(self.gray("mask2", i).astype(np.float32) / 255, self.prior)
        # place the source in the card, extending the room to the left
        pad_l = SRC_X
        G = cv2.copyMakeBorder(g, 0, 0, pad_l, 0, cv2.BORDER_REPLICATE)
        Mk = cv2.copyMakeBorder(m, 0, 0, pad_l, 0, cv2.BORDER_CONSTANT, value=0)
        G = G[-SRC_Y:-SRC_Y + h]; Mk = Mk[-SRC_Y:-SRC_Y + h]
        G[:, :pad_l + 30] = cv2.GaussianBlur(G, (0, 0), 14)[:, :pad_l + 30]
        p = (t - seg[0]) / max(seg[1] - seg[0], 0.1)
        k = 1.0 + 0.04 * ease_out(p)
        M = cv2.getRotationMatrix2D((w * 0.62, 360), 0, k)
        G = cv2.warpAffine(G, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
        Mk = cv2.warpAffine(Mk, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
        Mk = cv2.GaussianBlur(np.clip((Mk - 0.15) / 0.7, 0, 1), (0, 0), 1.1)
        lum = cv2.GaussianBlur(G, (0, 0), 2)
        a = np.clip(lum * 2.4, 0, 1)[..., None] * (0.3 + 0.7 * self.wall)
        ink = np.array(INK, np.float32) / 255
        room = ink * (1 - a) + (LIME / 255 * 0.8) * a
        room = room * (0.5 + 0.5 * self.wall) + np.clip(lum - 0.5, 0, 1)[..., None] * 0.25
        pg = np.clip((G - 0.03) / 0.92, 0, 1)
        person = np.dstack([pg, pg, pg])
        # light spill from the lit wall on his edges
        sl = np.zeros_like(Mk); sl[:, 6:] = Mk[:, :-6]
        sr = np.zeros_like(Mk); sr[:, :-6] = Mk[:, 6:]
        edge = cv2.GaussianBlur(np.clip(2 * Mk - sl - sr, 0, 1), (0, 0), 3) * Mk * 0.55
        person = person * (1 - edge[..., None]) + (LIME / 255) * pg[..., None].clip(0.5, 1) * edge[..., None]
        return room, person, Mk

    def big_word(self, lines):
        key = tuple(lines)
        if key in self._bw:
            return self._bw[key]
        w = CARD[2] - 60
        rows = []
        caps = [400] if len(lines) == 1 else [130, 270]
        for ln, cap in zip(lines, caps):
            r = txt(ln, "gothic", 400, WHITE)
            # stretch to the full width and a fixed row height, like the reference's tall type
            tw = min(w, int(r.width * cap / r.height * 1.9))
            rows.append(r.resize((tw, cap), Image.LANCZOS))
        gap = 10
        hh = sum(r.height for r in rows) + gap * (len(rows) - 1)
        im = Image.new("RGBA", (w, hh), (0, 0, 0, 0))
        y = 0
        for r in rows:
            im.alpha_composite(r, ((w - r.width) // 2, y)); y += r.height + gap
        im = vgrad(im, (255, 255, 255), LIMEt, 1.0, 0.55, mid=((245, 255, 215), 0.45))
        self._bw[key] = im
        return im

    def compose_speaker(self, i, t, seg):
        w, h = CARD[2], CARD[3]
        room, person, m = self.speaker(i, t, seg)
        bg = Image.fromarray((np.clip(room, 0, 1) * 255).astype(np.uint8)).convert("RGBA")
        cur = [b for b in BIG if b[0] <= t < b[1]]
        top_y = 70
        for on, off, lines, kick, align, ic in cur:
            im = self.big_word(lines)
            p = ease_out((t - on) / 0.22)
            vis = max(1, int(im.height * p))
            part = im.crop((0, 0, im.width, vis))
            paste(bg, part, w / 2, top_y + 34 + (im.height - vis) * 0.0, anchor="ct")
        bgn = np.asarray(bg.convert("RGB")).astype(np.float32) / 255
        out = bgn * (1 - m[..., None]) + person * m[..., None]
        img = Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8)).convert("RGBA")

        for on, off, lines, kick, align, ic in cur:
            im = self.big_word(lines)
            if kick:
                kt = txt(kick, "inter", 30, WHITE)
                kx = w / 2 if align == "c" else 44 + kt.width / 2
                paste(img, kt, kx, top_y, anchor="ct")
            if ic:
                pi = back_out((t - on - 0.1) / 0.35)
                iy = top_y + 34 + (im.height * (0.25 if len(lines) == 1 else 0.1))
                ix = w - 70 if ic not in ("camera", "eyes") else 92
                paste(img, sticker(ic, 84), ix, iy, scale=max(pi, 0.01), anchor="c")
        for on, off, kick in KICK_ONLY:
            if on <= t < off:
                kt = txt(kick, "inter", 30, WHITE)
                kx = w / 2 if kick != "WHAT I SEE ON" else 44 + kt.width / 2
                paste(img, kt, kx, top_y if not cur else top_y, anchor="ct", alpha=ease_out((t - on) / 0.15))
        for s_on, b_on, off, small, big in CAPS:
            st = min(x for x in (s_on, b_on) if x is not None)
            if not (st <= t < off):
                continue
            by = 618
            if big and t >= b_on:
                p = ease_out((t - b_on) / 0.18)
                bi = fit(txt(big, "gothic", 140, WHITE), w - 70, 88)
                paste(img, bi, w / 2, by + (1 - p) * 10, alpha=p, anchor="ct")
            if small and t >= s_on:
                p = ease_out((t - s_on) / 0.18)
                paste(img, txt(small, "urb500", 38, WHITE), w / 2, by - 50 + (1 - p) * 8, alpha=p, anchor="ct")
        if CHECKS[0][0] <= t < CHECKS_OFF:
            for k, (on, label) in enumerate(CHECKS):
                if t >= on:
                    p = ease_out((t - on) / 0.25)
                    paste(img, self.pill(label), 86 + (1 - p) * -30, 690 + k * 70, alpha=p)
        for on, off in BUBBLES:
            if on <= t < off:
                for k in range(3):
                    p = back_out((t - on - k * 0.09) / 0.32)
                    if p > 0.01:
                        paste(img, self.bubble(), w / 2 + (k - 1) * 120, 720, scale=p, anchor="c")
        return img

    @lru_cache(None)
    def pill(self, label):
        t = txt(label, "urb500", 34, INK)
        w, h = 386, 54
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((0, 0, w - 1, h - 1), 10, fill=LIMEt + (225,), outline=(235, 255, 180, 255), width=2)
        d.ellipse((16, h / 2 - 10, 36, h / 2 + 10), fill=INK + (255,))
        im.alpha_composite(t, (52, (h - t.height) // 2))
        return im

    @lru_cache(None)
    def bubble(self):
        r = 54
        S = r * 2 + 60
        im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        glow = Image.new("L", (S, S), 0)
        ImageDraw.Draw(glow).ellipse((30 - 8, 30 - 8, S - 30 + 8, S - 30 + 8), fill=200)
        glow = glow.filter(ImageFilter.GaussianBlur(12))
        gl = Image.new("RGBA", (S, S), LIMEt + (0,)); gl.putalpha(glow)
        im.alpha_composite(gl)
        c = Image.new("RGBA", (S * 4, S * 4), (0, 0, 0, 0))
        ImageDraw.Draw(c).ellipse((120, 120, S * 4 - 120, S * 4 - 120), fill=(252, 253, 248, 255))
        im.alpha_composite(c.resize((S, S), Image.LANCZOS))
        q = txt("?", "urb900", 82, INK)
        im.alpha_composite(q, ((S - q.width) // 2, (S - q.height) // 2))
        return im

    # ---- number cards ------------------------------------------------------
    def compose_number(self, t, n):
        img = self.vig.copy()
        w, h = CARD[2], CARD[3]
        t_num, (small, t_s), (title, t_t), ic = NUM_CARDS[n]
        ti = fit(txt(title, "gothic", 300, INK), 300 if n != 3 else 260, 104 if n != 3 else 84)
        si = txt(small, "urb400", 40, GREY)
        nh = ti.height + si.height + 12
        nr = txt(str(n), "anton", 300, WHITE)
        num = hgrad(nr.resize((int(nr.width * nh / nr.height), nh), Image.LANCZOS), (236, 255, 170), (150, 200, 10))
        tile = 40
        gw = num.width + 14 + max(ti.width, si.width + tile + 30)
        x0 = (w - gw) / 2 - 10
        ybot = 480
        nx = x0
        tx = x0 + num.width + 14
        # long shadows
        key = ("ls", n)
        if key not in self._bw:
            comp = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            comp.alpha_composite(num, (int(nx), int(ybot - num.height)))
            comp.alpha_composite(ti, (int(tx), int(ybot - ti.height)))
            self._bw[key] = long_shadow(comp, 150, 0.09)
        if t >= t_t:
            p = ease_out((t - t_t) / 0.4)
            ls = self._bw[key]
            paste(img, ls.crop((0, 0, ls.width, ls.height)), 0, 0, alpha=p)
        if t >= t_num:
            p = ease_out((t - t_num) / 0.32)
            vis = max(1, int(num.height * p))
            paste(img, num.crop((0, num.height - vis, num.width, num.height)), nx, ybot - vis)
        if t >= t_s:
            p = ease_out((t - t_s) / 0.25)
            paste(img, si, tx, ybot - ti.height - si.height - 10 + (1 - p) * 10, alpha=p)
            pi = back_out((t - t_s - 0.05) / 0.3)
            tl = Image.new("RGBA", (tile * 4, tile * 4), (0, 0, 0, 0))
            ImageDraw.Draw(tl).rounded_rectangle((0, 0, tile * 4 - 1, tile * 4 - 1), 40, fill=LIMEt + (255,))
            tl = tl.resize((tile, tile), Image.LANCZOS)
            tl.alpha_composite(glyph(ic, tile - 10, INK), (5, 5))
            paste(img, tl, tx + max(ti.width, si.width + tile + 20) - tile / 2, ybot - ti.height - si.height / 2 - 12,
                  scale=max(pi, 0.01), anchor="c")
        if t >= t_t:
            p = ease_out((t - t_t) / 0.3)
            vis = max(1, int(ti.width * p))
            paste(img, ti.crop((0, 0, vis, ti.height)), tx, ybot - ti.height)
        return img

    def compose_insp(self, t):
        img = self.soft.copy()
        w = CARD[2]
        if t >= INSP["vault"]:
            p = ease_out((t - INSP["vault"]) / 0.45)
            grow = 1 + 0.12 * ease_out((t - INSP["house"]) / 0.4) if t >= INSP["house"] else 1
            v = prop_vault(330)
            shd = Image.new("RGBA", v.size, (40, 52, 10, 0))
            shd.putalpha(v.getchannel("A").point(lambda a: int(a * 0.18)).filter(ImageFilter.GaussianBlur(16)))
            paste(img, shd, 110 + 20 - (1 - p) * 200, 300 + 40, scale=grow, anchor="c")
            paste(img, v, 110 - (1 - p) * 200, 300, scale=grow, anchor="c")
            pt = ease_out((t - INSP["vault"] - 0.15) / 0.3)
            ins = vgrad(fit(txt("INSPIRATION", "gothic", 200, INK), 999, 70), INK, LIME_DEEP)
            paste(img, ins, 300, 218 + (1 - pt) * 12, alpha=pt)
            paste(img, txt("vault", "urb400", 30, GREY), 302, 218 + ins.height + 2, alpha=pt)
        if t >= INSP["book"]:
            p = ease_out((t - INSP["book"]) / 0.45)
            b = prop_book(300)
            shd = Image.new("RGBA", b.size, (40, 52, 10, 0))
            shd.putalpha(b.getchannel("A").point(lambda a: int(a * 0.2)).filter(ImageFilter.GaussianBlur(18)))
            paste(img, shd, 470 + 30, 640 + 50 + (1 - p) * 220, anchor="c")
            paste(img, b, 470, 640 + (1 - p) * 220, anchor="c")
        if t >= INSP["refs"]:
            p = ease_out((t - INSP["refs"]) / 0.3)
            s = txt("thousands of", "urb400", 32, GREY)
            r = vgrad(fit(txt("REFERENCES", "gothic", 200, INK), 999, 74), INK, LIME_DEEP)
            paste(img, s, 104, 628 + (1 - p) * 10, alpha=p)
            paste(img, r, 104, 628 + s.height + 10 + (1 - p) * 10, alpha=p)
        return img

    def compose_fx(self, t):
        img = self.soft_plus.copy()
        for k, (on, label, ic) in enumerate(FX_ROWS):
            if t < on:
                continue
            p = ease_out((t - on) / 0.3)
            y = 252 + k * 96
            paste(img, self.fx_pill(label), 84 + (1 - p) * 24, y, alpha=p)
            paste(img, glyph(ic, 36, OLIVE), 470, y + 23, alpha=p, anchor="c")
        return img

    @lru_cache(None)
    def fx_pill(self, label):
        w, h = 348, 48
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((0, 0, w - 1, h - 1), 9, fill=LIMEt + (170,), outline=LIME_DEEP + (255,), width=2)
        d.ellipse((14, h / 2 - 10, 34, h / 2 + 10), fill=INK + (255,))
        t = txt(label, "urb500", 27, INK)
        im.alpha_composite(t, (46, (h - t.height) // 2))
        return im

    # ---- frame -------------------------------------------------------------
    def frame(self, fi):
        if not hasattr(self, "_bw"):
            self._bw = {}
        t = fi / FPS
        i = fi + 1
        seg = v1.seg_at(t)
        kind = seg[2]
        if kind == "spk":
            content = self.compose_speaker(i, t, seg)
        elif kind == "num":
            content = self.compose_number(t, seg[3])
        elif kind == "insp":
            content = self.compose_insp(t)
        else:
            content = self.compose_fx(t)
        dt = t - seg[0]
        if seg[0] > 0 and dt < 0.17:
            k = 1.0 + 0.04 * (1 - ease_out(dt / 0.17))
            cw, ch = int(CARD[2] * k), int(CARD[3] * k)
            content = content.resize((cw, ch), Image.BILINEAR).crop(
                ((cw - CARD[2]) // 2, (ch - CARD[3]) // 2, (cw - CARD[2]) // 2 + CARD[2], (ch - CARD[3]) // 2 + CARD[3]))
        content.putalpha(self.card_mask)
        page = self.page.copy()
        b = Image.fromarray(self.gray("before_up", i)).convert("RGBA")
        b.putalpha(self.before_mask)
        page.alpha_composite(b, (BEFORE[0], BEFORE[1]))
        page.alpha_composite(self.card_shadow[0], self.card_shadow[1])
        page.alpha_composite(content, (CARD[0], CARD[1]))
        return np.asarray(page.convert("RGB"))


# ===========================================================================
def prep(ref, work):
    v1.prep(ref, work)   # B&W "Before" panel, voice stem, transcript
    a2, m2 = os.path.join(work, "after2"), os.path.join(work, "mask2")
    os.makedirs(a2, exist_ok=True); os.makedirs(m2, exist_ok=True)
    if not os.listdir(a2):
        sh(f'ffmpeg -v error -i "{ref}" -vf "crop={v1.BEFORE_CROP},hqdn3d=1.5:1.5:4:4,'
           f'scale={SRC_W}:{SRC_H}:flags=lanczos,unsharp=5:5:0.6:5:5:0,format=gray" "{a2}/%04d.png"')
    from rembg import remove, new_session
    sess = new_session("u2net_human_seg")
    for f in sorted(os.listdir(a2)):
        o = os.path.join(m2, f)
        if not os.path.exists(o):
            remove(Image.open(os.path.join(a2, f)).convert("RGB"), session=sess, only_mask=True).save(o)
    fonts_dir(work)
    mask_prior(work)


def mask_prior(work):
    """The cut-out model sometimes drops his dark T-shirt. He barely moves, so a
    median of the good masks, kept below the chin, backs it up."""
    d = os.path.join(work, "mask2")
    ms = [cv2.imread(os.path.join(d, f), cv2.IMREAD_GRAYSCALE) for f in sorted(os.listdir(d))[::3]]
    area = np.array([(m[600:] > 128).mean() for m in ms])
    good = np.stack([m for m, a in zip(ms, area) if a >= np.median(area) * 0.9])
    pr = (np.median(good, 0) > 128).astype(np.uint8) * 255
    pr = cv2.erode(pr, np.ones((15, 15), np.uint8))
    y = np.arange(pr.shape[0])[:, None]
    x = np.arange(pr.shape[1])[None, :]
    pr = (pr * np.clip((y - 560) / 80, 0, 1) * np.clip((x - 20) / 80, 0, 1)).astype(np.uint8)
    cv2.imwrite(os.path.join(work, "mask_prior.png"), cv2.GaussianBlur(pr, (0, 0), 4))


R = None


def _init(work):
    global R
    R = Renderer(work)


def _frame(fi):
    return R.frame(fi).tobytes()


def render(work, only=None):
    from multiprocessing import Pool
    nfr = int(round(END * FPS))
    if not os.path.exists(os.path.join(work, "mask_prior.png")):
        mask_prior(work)
    if only is not None:
        _init(work)
        for fi in only:
            Image.fromarray(R.frame(fi)).save(os.path.join(work, f"v2_{fi:04d}.png"))
        return
    vid = os.path.join(work, "video_v2.mp4")
    p = subprocess.Popen(f'ffmpeg -v error -y -f rawvideo -pix_fmt rgb24 -s {W}x{H} -r {FPS} -i - '
                         f'-c:v libx264 -preset slow -crf 16 -pix_fmt yuv420p "{vid}"', shell=True, stdin=subprocess.PIPE)
    with Pool(3, initializer=_init, initargs=(work,)) as pool:
        for k, buf in enumerate(pool.imap(_frame, range(nfr), chunksize=4)):
            p.stdin.write(buf)
            if k % 300 == 0:
                print(f"frame {k}/{nfr}", flush=True)
    p.stdin.close(); p.wait()
    mix, master = os.path.join(work, "mix.wav"), os.path.join(work, "master.wav")
    v1.build_audio(work, mix)
    v1.loudnorm(mix, master)
    out = os.path.join(work, "AVE_Before_After_V2.mp4")
    sh(f'ffmpeg -v error -y -i "{vid}" -i "{master}" -c:v copy -c:a aac -b:a 256k -shortest -movflags +faststart "{out}"')
    print(out)


if __name__ == "__main__":
    cmd, ref, work = sys.argv[1:4]
    if cmd == "prep":
        prep(ref, work)
    elif cmd == "render":
        render(work)
    elif cmd == "stills":
        render(work, only=[int(float(x) * FPS) for x in sys.argv[4:]])
