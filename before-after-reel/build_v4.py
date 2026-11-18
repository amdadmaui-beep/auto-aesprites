"""AVE Studio · Before / After reel, V4: heavy-type pass.

Same Before / After layout, colour footage, cards, transitions and sound as V3,
with the whole type system rebuilt in the style the user asked for
(thick geometric black weight, lowercase):
  * big words in Poppins Black with a pale-lime -> lime -> olive gradient,
    sitting behind the speaker, whipping in with horizontal motion blur;
  * a light-weight white kicker overlapping each big word's top-left corner;
  * bold-italic add-on words tucked under the big word's bottom-right;
  * an outlined number with a filled word over it ("3 tips");
  * one-word lowercase captions at chest height, with corner brackets on a few lines;
  * every other piece of text in the reel (cards, pills, page) moved to Poppins.

Usage: python build_v4.py render REF.mp4 WORK MUSIC.mp3 [MUSIC_START]
       python build_v4.py stills REF.mp4 WORK 1.0 ...
"""
import json, math, os, subprocess, sys
from functools import lru_cache

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import build as v1
import build_v2 as v2
import build_v3 as v3
from build_v3 import expo, spring, smooth, clamp01, place

W, H, FPS, END = v3.W, v3.H, v3.FPS, v3.END
CARD = v3.CARD
INK, PAPER, WHITE = v3.INK, v3.PAPER, v3.WHITE
LIMEt = v3.LIMEt
PALE, OLIVE = (238, 255, 196), (128, 168, 18)


# ---- Poppins everywhere -------------------------------------------------------------
@lru_cache(None)
def poppins(kind, size):
    name = {"black": "Black", "blacki": "BlackItalic", "xbi": "ExtraBoldItalic", "bold": "Bold",
            "semi": "SemiBold", "med": "Medium", "light": "Light"}[kind]
    return ImageFont.truetype(os.path.join(v2.FD, f"Poppins-{name}.ttf"), size)


def font_map(kind, size):
    if kind in ("gothic", "gothicw", "anton"):
        return poppins("black", size)
    if kind.startswith("urb"):
        w = int(kind[3:])
        return poppins("light" if w <= 400 else "med" if w <= 500 else "semi" if w <= 600 else "bold" if w <= 700 else "black", size)
    if kind == "inter":
        return poppins("med", size)
    return v2._font_orig(kind, size)


v2._font_orig = v2.font
v2.font = font_map
v3.font = font_map
v3.NUM_CARDS = {1: (6.10, ("lack of", 6.62), ("direction", 7.00)),
                2: (20.58, ("bad", 21.12), ("design", 21.36)),
                3: (31.14, ("poor", 31.72), ("post-production", 31.94))}

# ---- the type events ------------------------------------------------------------------
# (start, end, kicker, big, extra, extra_time)
TYPE = [
    (0.62, 2.76, "your", "edits", None, None),
    (3.50, 5.36, "on", "instagram", None, None),
    (7.70, 8.96, "a good", "edit", None, None),
    (9.26, 11.50, "know", "exactly", "what you want", 9.74),
    (17.90, 20.47, "you're gonna", "lost", "not that good", 19.40),
    (22.14, 24.87, "is the most important", "design", "skill", 23.34),
    (29.24, 30.47, "you're a", "beginner", None, None),
    (33.02, 35.42, "post", "production", "to life", 34.74),
    (35.80, 36.90, "look into", "effects", None, None),
    (42.50, END, "remember these", "#3 tips", "looks boring", 44.02),
]
BRACKETS = [(9.74, 11.50), (24.87, 29.20), (33.64, 35.42)]


@lru_cache(None)
def word_img(s, kind, size, color, stroke=0):
    f = poppins(kind, size)
    l, t, r, b = f.getbbox(s, stroke_width=stroke)
    im = Image.new("RGBA", (r - l + 16, b - t + 16), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((8 - l, 8 - t), s, font=f, fill=color + (255,), stroke_width=stroke,
                            stroke_fill=color + (255,))
    return im


def grad(im, top=PALE, mid=LIMEt, bot=OLIVE):
    a = np.asarray(im.getchannel("A")).astype(np.float32)
    h = a.shape[0]
    y = np.linspace(0, 1, h)[:, None, None]
    t, m, b = (np.array(c, np.float32) for c in (top, mid, bot))
    col = np.where(y < 0.5, t + (m - t) * (y / 0.5), m + (b - m) * ((y - 0.5) / 0.5))
    return Image.fromarray(np.dstack([np.broadcast_to(col, a.shape + (3,)), a[..., None]]).clip(0, 255).astype(np.uint8))


@lru_cache(None)
def big_word(s, maxw):
    """Poppins Black, lowercase, gradient fill; '#3 tips' = outlined number + filled word."""
    size = 190
    if s.startswith("#"):
        num, rest = s[1:].split(" ", 1)
        fill = word_img(num, "black", size, WHITE)
        outer = word_img(num, "black", size, WHITE, stroke=5)
        ring = np.clip(np.asarray(outer.getchannel("A")).astype(np.int16)
                       - np.pad(np.asarray(fill.getchannel("A")), ((5, 5), (5, 5)))[:outer.height, :outer.width], 0, 255)
        o = Image.new("RGBA", outer.size, LIMEt + (0,)); o.putalpha(Image.fromarray(ring.astype(np.uint8)))
        wd = grad(word_img(rest, "black", int(size * 0.62), WHITE))
        im = Image.new("RGBA", (o.width + wd.width - 30, o.height), (0, 0, 0, 0))
        im.alpha_composite(o, (0, 0))
        im.alpha_composite(wd, (o.width - 40, int(o.height * 0.30)))
    else:
        im = grad(word_img(s, "black", size, WHITE))
    if im.width > maxw:
        k = maxw / im.width
        im = im.resize((maxw, max(1, int(im.height * k))), Image.LANCZOS)
    return im


def hblur(im, px):
    if px < 2:
        return im
    a = np.asarray(im).astype(np.float32)
    return Image.fromarray(cv2.blur(a, (int(px) | 1, 1)).clip(0, 255).astype(np.uint8))


class Renderer(v3.Renderer):
    def __init__(self, work):
        super().__init__(work)
        self.words = json.load(open(os.path.join(work, "words.json")))

    def whip(self, t, on, off):
        """Return (x offset, blur px, alpha) for a whip in / whip out."""
        p = expo((t - on) / 0.38)
        x = (1 - p) * 110
        blur = (1 - p) * 70
        a = min(1, p * 1.6)
        last = any(abs(off - b) < 0.02 for b in v3.BOUNDS) or off >= END - 0.01
        if not last and t > off - 0.16:
            q = smooth((t - (off - 0.16)) / 0.16)
            x -= q * 120; blur += q * 70; a *= 1 - q
        return x, blur, a

    def compose_speaker(self, i, t, seg, t_ov=None):
        t_ov = t if t_ov is None else t_ov
        w, h = CARD[2], CARD[3]
        room, person, m = self.speaker(i, t, seg)
        bg = Image.fromarray((np.clip(room, 0, 1) * 255).astype(np.uint8)).convert("RGBA")
        front = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        top = 112
        for on, off, kick, big, extra, et in TYPE:
            if not (on - 0.12 <= t_ov < off):
                continue
            bw = big_word(big, w - 40)
            bx = (w - bw.width) / 2
            dx, bl, al = self.whip(t_ov, on, off)
            # soft shadow + word, behind him
            sh = Image.new("RGBA", bw.size, (0, 0, 0, 0))
            sh.putalpha(bw.getchannel("A").filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * 0.45)))
            place(bg, hblur(sh, bl), bx + dx, top + 10, alpha=al)
            place(bg, hblur(bw, bl), bx + dx, top, alpha=al)
            # kicker overlaps the top-left corner (in front)
            if kick:
                kp = expo((t_ov - on + 0.12) / 0.35)
                ki = word_img(kick, "light", 52 if len(kick) < 10 else 40, WHITE)
                kx = bx + 10 + (1 - kp) * -30
                place(front, ki, kx, top - ki.height * 0.62, alpha=kp * (al if t_ov > on else 1))
            # bold-italic add-on under the bottom-right
            if extra and t_ov >= et:
                q = spring(t_ov - et, 14, 0.6)
                ei = word_img(extra, "blacki", 50, WHITE)
                if ei.width > w - 60:
                    ei = ei.resize((w - 60, int(ei.height * (w - 60) / ei.width)), Image.LANCZOS)
                ex = min(bx + bw.width - ei.width * 0.75, w - ei.width - 16)
                place(front, ei, ex + (1 - min(q, 1)) * 40, top + bw.height * 0.78, alpha=min(1, q * 1.6) * al,
                      scale=1.12 - 0.12 * min(q, 1))
        bgn = np.asarray(bg.convert("RGB")).astype(np.float32) / 255
        out = bgn * (1 - m[..., None]) + person * m[..., None]
        img = Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8)).convert("RGBA")
        img.alpha_composite(front)

        # one-word lowercase captions at chest height
        cur = [x for x in self.words if x[0] - 0.02 <= t_ov < max(x[1], x[0] + 0.18) + 0.06]
        if cur:
            st, en, wd = cur[-1]
            wd = wd.lower().strip(".,!?")
            q = expo((t_ov - st + 0.02) / 0.16)
            ci = word_img(wd, "med", 40, WHITE)
            cs = Image.new("RGBA", ci.size, (0, 0, 0, 0))
            cs.putalpha(ci.getchannel("A").filter(ImageFilter.GaussianBlur(8)).point(lambda v: int(v * 0.6)))
            cy = 620
            place(img, cs, w / 2, cy + 4, alpha=q, anchor="c")
            place(img, ci, w / 2, cy, alpha=q, scale=1.14 - 0.14 * q, anchor="c")
            if any(a <= t_ov < b for a, b in BRACKETS):
                d = ImageDraw.Draw(img)
                bw2, bh2, L = max(ci.width + 70, 220), 96, 22
                x0, y0, x1, y1 = w / 2 - bw2 / 2, cy - bh2 / 2, w / 2 + bw2 / 2, cy + bh2 / 2
                for (cx, cy2, sx, sy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
                    d.line((cx, cy2, cx + sx * L, cy2), fill=WHITE + (230,), width=3)
                    d.line((cx, cy2, cx, cy2 + sy * L), fill=WHITE + (230,), width=3)

        # checklist pills and question bubbles from V3
        if v3.CHECKS[0][0] <= t_ov < v3.CHECKS_OFF:
            for k_, (on, label) in enumerate(v3.CHECKS):
                if t_ov >= on:
                    p = spring(t_ov - on, 13, 0.75)
                    self.glass_pill(img, label, 74 - (1 - p) * 70, 676 + k_ * 74, min(1, p * 1.3), (1 - clamp01(p)) * 6)
        for on, off in v3.BUBBLES:
            if on <= t_ov < off:
                ek = v3.exit_k(t_ov, off, 0.22)
                for k_ in range(3):
                    p = spring(t_ov - on - k_ * 0.08, 16, 0.5)
                    if p > 0.01:
                        place(img, self.bubble(), w / 2 + (k_ - 1) * 122, 726, scale=max(p, 0.01) * (0.85 + 0.15 * ek),
                              alpha=ek * min(1, p * 2), rot=(1 - clamp01(p)) * -14, anchor="c")
        return img


v3.SFX[:] = ([(t, "whoosh") for t in v3.BOUNDS]
             + [(t, "air") for t, *_ in TYPE]
             + [(t, "thock") for t in (6.10, 20.58, 31.14)]
             + [(t, "bloop") for t in (5.36, 25.26, 26.46, 27.26, 42.50, 12.20)]
             + [(t + 0.22, "ding") for t, _ in v3.FX_ROWS])

R = None


def _init(work):
    global R
    v2.FD = v2.fonts_dir(work)
    R = Renderer(work)


def _frame(fi):
    return R.frame(fi).tobytes()


def render(work, music=None, start=24.0, only=None):
    from multiprocessing import Pool
    nfr = int(round(END * FPS))
    if only is not None:
        _init(work)
        for fi in only:
            Image.fromarray(R.frame(fi)).save(os.path.join(work, f"v4_{fi:04d}.png"))
        return
    vid = os.path.join(work, "video_v4.mp4")
    p = subprocess.Popen(f'ffmpeg -v error -y -f rawvideo -pix_fmt rgb24 -s {W}x{H} -r {FPS} -i - '
                         f'-c:v libx264 -preset slow -crf 15 -pix_fmt yuv420p "{vid}"', shell=True, stdin=subprocess.PIPE)
    with Pool(3, initializer=_init, initargs=(work,)) as pool:
        for buf in pool.imap(_frame, range(nfr), chunksize=4):
            p.stdin.write(buf)
    p.stdin.close(); p.wait()
    mix, master = os.path.join(work, "mix_v4.wav"), os.path.join(work, "master_v4.wav")
    v3.build_audio(work, music, start, mix)
    v1.loudnorm(mix, master)
    out = os.path.join(work, "AVE_Before_After_V4.mp4")
    v1.sh(f'ffmpeg -v error -y -i "{vid}" -i "{master}" -c:v copy -c:a aac -b:a 256k -shortest -movflags +faststart "{out}"')
    print(out)


if __name__ == "__main__":
    cmd, ref, work = sys.argv[1:4]
    if cmd == "render":
        render(work, sys.argv[4], float(sys.argv[5]) if len(sys.argv) > 5 else 24.0)
    elif cmd == "stills":
        render(work, only=[int(round(float(x) * FPS)) for x in sys.argv[4:]])
