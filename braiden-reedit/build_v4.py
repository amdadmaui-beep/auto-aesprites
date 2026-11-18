"""Braiden re-edit V4: V3's edit in AVE colours, laid out with no empty space.

Palette swap (teal -> AVE): accent boxes, band, wheel, coin and keywords use
lime #C8FF2E with ink #0E0E0E text on lime; the page is ink, off-white text.
Layout (1080x1920): AVE header, raw panel, edit panel, branded footer with
the DM "SAMPLE" call to action and the credit to @braidenshaw.

Usage: python build_v4.py render SOURCE.mp4 WORK [MUSIC.mp3 START]
       python build_v4.py stills SOURCE.mp4 WORK 1.0 ...
"""
import math, os, subprocess, sys
from functools import lru_cache

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
import importlib.util  # noqa: E402
_spec = importlib.util.spec_from_file_location("braiden_v3", os.path.join(HERE, "build_v3.py"))
b3 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(b3)
b2, b1, v1 = b3.b2, b3.b1, b3.v1
from build_v3 import expo, smooth, place  # noqa: E402

W, H, FPS, PW, PH, N, END = b3.W, b3.H, b3.FPS, b3.PW, b3.PH, b3.N, b3.END
INK, PAPER, LIME = (14, 14, 14), (243, 242, 238), (200, 255, 46)
OLIVE = (96, 128, 8)
MUTED = (138, 135, 127)
AVE_FONTS = os.path.join(b1.ROOT, "ave-promo", "film", "fonts")

# layout
HEAD_H = 236
RAW_Y = HEAD_H
EDIT_Y = RAW_Y + PH + 18
FOOT_Y = EDIT_Y + PH

# ---- palette swap ---------------------------------------------------------------
for mod in (b2, b3):
    mod.TEAL, mod.TEAL_L, mod.TEAL_D = LIME, LIME, INK
b3.BOX_FG = INK          # "Happiness" on the lime box
b3.BAND_FG = INK         # words on the lime band


@lru_cache(None)
def banknote(w=220, h=100):
    S = 3
    im = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w * S - 1, h * S - 1), 8 * S, fill=(22, 26, 12, 235), outline=LIME + (255,), width=2 * S)
    d.rounded_rectangle((8 * S, 8 * S, (w - 8) * S, (h - 8) * S), 6 * S, outline=LIME + (130,), width=S)
    d.ellipse(((w / 2 - 26) * S, (h / 2 - 26) * S, (w / 2 + 26) * S, (h / 2 + 26) * S), outline=LIME + (255,), width=2 * S)
    d.text((w / 2 * S, h / 2 * S), "$", font=b2.font("serif800", 40 * S), fill=LIME + (255,), anchor="mm")
    for cx in (34, w - 34):
        d.text((cx * S, h / 2 * S), "100", font=b2.font("urb700", 16 * S), fill=LIME + (220,), anchor="mm")
    return im.resize((w, h), Image.LANCZOS)


@lru_cache(None)
def coin_face(r=90):
    S = 3
    im = Image.new("RGBA", (r * 2 * S, r * 2 * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((0, 0, r * 2 * S - 1, r * 2 * S - 1), fill=LIME + (255,))
    d.ellipse((10 * S, 10 * S, (2 * r - 10) * S, (2 * r - 10) * S), outline=INK + (255,), width=4 * S)
    d.text((r * S, r * S), "$", font=b2.font("serif900", int(r * 1.15) * S), fill=INK + (255,), anchor="mm")
    return im.resize((2 * r, 2 * r), Image.LANCZOS)


b2.banknote, b2.coin_face = banknote, coin_face
b3.banknote = banknote
_TEAL_D_RIM = OLIVE


@lru_cache(None)
def ave_font(kind, size):
    files = {"xb": "InterDisplay-ExtraBold.otf", "md": "InterDisplay-Medium.otf",
             "serif": "InstrumentSerif-italic-400.woff2", "mono": "JetBrainsMono-normal-500.woff2"}
    return ImageFont.truetype(os.path.join(AVE_FONTS, files[kind]), size)


def t_img(s, kind, size, color, track=0):
    f = ave_font(kind, size)
    ws = [f.getlength(c) for c in s] if track else [f.getlength(s)]
    im = Image.new("RGBA", (int(sum(ws) + track * len(s)) + 24, int(size * 1.5)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if track:
        x = 4
        for c, cw in zip(s, ws):
            d.text((x, 4), c, font=f, fill=color + (255,)); x += cw + track
    else:
        d.text((4, 4), s, font=f, fill=color + (255,))
    return im.crop(im.getbbox())


class Renderer(b3.Renderer):
    def __init__(self, work):
        super().__init__(work)
        self.page = self.build_page()

    def grade(self, a):
        """Neutral, slightly warm, a touch of contrast (no teal push)."""
        a = np.clip((a - 0.015) * 1.07, 0, 1)
        a = a * np.array([1.015, 1.0, 0.975])
        return np.clip(a * self.vig, 0, 1)

    def leak(self, t):
        v = 0.0
        for t0, amt in b3.LEAKS:
            d = t - t0
            if -0.15 <= d < 0.6:
                v = max(v, amt * (smooth((d + 0.15) / 0.15) if d < 0 else 1 - smooth(d / 0.6)))
        if v <= 0.01:
            return None
        cx = PW * (0.2 + 0.6 * (0.5 + 0.5 * math.sin(t * 2.3)))
        g1 = np.exp(-(((self.xx - cx) / 380) ** 2 + ((self.yy - PH * 0.3) / 260) ** 2))
        g2 = np.exp(-(((self.xx - (PW - cx)) / 300) ** 2 + ((self.yy - PH * 0.8) / 220) ** 2))
        return (g1[..., None] * np.array([1.0, 0.66, 0.34]) + g2[..., None] * np.array([0.62, 0.85, 0.12])) * v

    def build_page(self):
        img = Image.new("RGBA", (W, H), INK + (255,))
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        g = np.exp(-(((xx - 960) / 640) ** 2 + ((yy - 40) / 360) ** 2)) * 0.12 \
            + np.exp(-(((xx - 80) / 700) ** 2 + ((yy - 1900) / 420) ** 2)) * 0.10
        arr = np.array(INK, np.float32) * (1 - g[..., None]) + np.array(LIME, np.float32) * g[..., None]
        img = Image.fromarray(arr.astype(np.uint8)).convert("RGBA")
        d = ImageDraw.Draw(img)
        # header: wordmark, STUDIO, and a RE-EDIT chip
        wm = Image.open(os.path.join(b1.ROOT, "brand", "logos", "ave-wordmark-paper.png")).convert("RGBA")
        wm = wm.resize((int(wm.width * 58 / wm.height), 58), Image.LANCZOS)
        img.alpha_composite(wm, (56, 96))
        st = t_img("STUDIO", "mono", 20, MUTED, track=8)
        img.alpha_composite(st, (56 + (wm.width - st.width) // 2, 164))
        chip = t_img("RE-EDIT", "mono", 24, INK, track=5)
        cw = chip.width + 44
        d.rounded_rectangle((W - 56 - cw, 104, W - 56, 150), 23, fill=LIME + (255,))
        img.alpha_composite(chip, (W - 56 - cw + 22, 104 + (46 - chip.height) // 2))
        # panel labels
        for y, lab, fill, fg in ((RAW_Y + 20, "RAW", (28, 27, 25), PAPER), (EDIT_Y + 20, "EDITED BY AVE", LIME, INK)):
            t = t_img(lab, "mono", 22, fg, track=4)
            self._labels = getattr(self, "_labels", []) + [(t, fill, y)]
        # footer: CTA + credit
        fy = FOOT_Y + 64
        a = t_img("DM", "xb", 76, PAPER)
        b = t_img("“SAMPLE”", "xb", 76, INK)
        gap = 22
        tw = a.width + gap + b.width + 28
        x = (W - tw) / 2
        d.rounded_rectangle((x + a.width + gap - 4, fy - 10, x + tw + 4, fy + b.height + 14), 14, fill=LIME + (255,))
        img.alpha_composite(a, (int(x), fy + b.height - a.height))
        img.alpha_composite(b, (int(x + a.width + gap + 10), fy))
        s1 = t_img("Get your first sample", "md", 40, MUTED)
        s2 = t_img("edit.", "serif", 50, PAPER)
        tw2 = s1.width + 12 + s2.width
        img.alpha_composite(s1, (int((W - tw2) / 2), fy + 120))
        img.alpha_composite(s2, (int((W - tw2) / 2 + s1.width + 12), fy + 120 + s1.height - s2.height + 8))
        cr = t_img("Original video: @braidenshaw", "md", 28, MUTED)
        img.alpha_composite(cr, ((W - cr.width) // 2, H - 96))
        return img

    def frame(self, fi):
        t = fi / FPS
        i = fi + 1
        page = self.page.copy()
        raw = self.raw(i).resize((PW, PH), Image.LANCZOS).convert("RGBA")
        page.alpha_composite(raw, (0, RAW_Y))
        page.alpha_composite(self.frame_edit(i, t), (0, EDIT_Y))
        d = ImageDraw.Draw(page)
        for lab, fill, y in self._labels:
            w = lab.width + 36
            d.rounded_rectangle((24, y, 24 + w, y + 40), 20, fill=fill + (235,))
            page.alpha_composite(lab, (24 + 18, y + (40 - lab.height) // 2))
        return np.asarray(page.convert("RGB"))


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
            Image.fromarray(R.frame(fi)).save(os.path.join(work, f"v4_{fi:04d}.png"))
        return
    vid = os.path.join(work, "video_v4.mp4")
    p = subprocess.Popen(f'ffmpeg -v error -y -f rawvideo -pix_fmt rgb24 -s {W}x{H} -r {FPS} -i - '
                         f'-c:v libx264 -preset slow -crf 14 -pix_fmt yuv420p "{vid}"', shell=True, stdin=subprocess.PIPE)
    with Pool(3, initializer=_init, initargs=(work,)) as pool:
        for buf in pool.imap(_frame, range(N), chunksize=3):
            p.stdin.write(buf)
    p.stdin.close(); p.wait()
    b1.SFX[:] = b3.SFX
    mix, master = os.path.join(work, "mix_v4.wav"), os.path.join(work, "master_v4.wav")
    b1.build_audio(work, mix, music, start)
    v1.loudnorm(mix, master)
    out = os.path.join(work, "AVE_Braiden_Reedit_V4.mp4")
    v1.sh(f'ffmpeg -v error -y -i "{vid}" -i "{master}" -c:v copy -c:a aac -b:a 256k -shortest -movflags +faststart "{out}"')
    print(out)


if __name__ == "__main__":
    cmd, src, work = sys.argv[1:4]
    if cmd == "render":
        render(work, sys.argv[4] if len(sys.argv) > 4 else None, float(sys.argv[5]) if len(sys.argv) > 5 else 0.0)
    elif cmd == "stills":
        render(work, only=[int(round(float(x) * FPS)) for x in sys.argv[4:]])
