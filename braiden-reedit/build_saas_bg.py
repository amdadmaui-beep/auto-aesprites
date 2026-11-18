"""Full-screen SaaS-style edit that keeps Braiden's real studio background.

Same graphics and timing as build_saas_full.py, but the footage fills the
frame (9:16 crop that follows him), big words sit behind him using the
cut-out mask, and the type is off-white for the dark set. Inverted flashes are
built from the mask so the background stays black.

Usage: python build_saas_bg.py render SOURCE.mp4 WORK [MUSIC.mp3 START]
       python build_saas_bg.py stills SOURCE.mp4 WORK 1.0 ...
"""
import math, os, subprocess, sys
from functools import lru_cache

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
import importlib.util  # noqa: E402
_spec = importlib.util.spec_from_file_location("braiden_saas_full", os.path.join(HERE, "build_saas_full.py"))
sf = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(sf)
from build_v3 import expo, spring, smooth, clamp01, place  # noqa: E402

W, H, FPS, N, END = sf.W, sf.H, sf.FPS, sf.N, sf.END
INK, PAPER, LIME = sf.INK, sf.PAPER, sf.LIME
b1, v1 = sf.b1, sf.v1


@lru_cache(None)
def sparkle_paper(size=40):
    S = 4
    im = Image.new("RGBA", (size * S, size * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    m = size * S / 2; t = size * S * 0.09
    d.rectangle((m - t, 0, m + t, size * S), fill=PAPER + (255,)); d.rectangle((0, m - t, size * S, m + t), fill=PAPER + (255,))
    return im.resize((size, size), Image.LANCZOS)


sf.sparkle = lambda size=40: Image.new("RGBA", (2, 2), (0, 0, 0, 0))   # no sparkle crosses


class Renderer(sf.Renderer):
    def __init__(self, work):
        super().__init__(work)
        yy = np.arange(H, dtype=np.float32)[:, None]
        # soft darkening at the top so the typed lines read on any shot
        self.top_shade = (1 - 0.45 * np.clip((900 - yy) / 900, 0, 1))[..., None]

    def zoom(self, t):
        keys = [(0.0, 1.45), (1.25, 1.45), (1.62, 1.05), (3.04, 1.0), (3.13, 1.35), (3.5, 1.08), (6.40, 1.04),
                (6.7, 1.0), (8.70, 1.0), (8.77, 1.35), (9.15, 1.05), (10.4, 1.03), (10.7, 1.0), (12.2, 1.0),
                (14.4, 1.12), (15.9, 1.12), (16.2, 1.2), (END, 1.24)]
        for (a, za), (b, zb) in zip(keys[:-1], keys[1:]):
            if a <= t < b:
                return za + (zb - za) * (expo((t - a) / (b - a)) if zb < za else smooth((t - a) / (b - a)))
        return keys[-1][1]

    TOP = 360   # extra wall above him (extended from the real wall) so graphics have room

    def footage(self, i, t, z):
        k = next(n for n, (a, b) in enumerate(sf.SHOTS) if a <= t < b or n == len(sf.SHOTS) - 1)
        _, cx, top, bot = self.shot_geo[k]
        T = self.TOP
        src = np.asarray(self.raw(i)).astype(np.float32) / 255
        ext = cv2.copyMakeBorder(src, T, 0, 0, 0, cv2.BORDER_REFLECT)
        soft = cv2.GaussianBlur(ext[:T + 60], (0, 0), 22)
        yy = np.arange(T + 60, dtype=np.float32)[:, None, None]
        blend = np.clip((T + 60 - yy) / 90, 0, 1)
        dark = 0.55 + 0.45 * (yy / (T + 60))
        ext[:T + 60] = ext[:T + 60] * (1 - blend) + soft * dark * blend
        mk = cv2.copyMakeBorder(np.asarray(self.mask(i)).astype(np.float32) / 255, T, 0, 0, 0, cv2.BORDER_CONSTANT, value=0)
        He = 608 + T
        ch = He / z
        cw = ch * W / H
        head = T + top + 0.12 * (bot - top)
        cy = He / 2 + (head - He / 2) * clamp01((z - 1) / 0.35)
        dx = 3 * math.sin(t * 1.3) + 1.5 * math.sin(t * 2.9)
        dy = 2 * math.sin(t * 1.7 + 1)
        x0 = min(max(cx - cw / 2 + dx, 0), 1080 - cw)
        y0 = min(max(cy - ch / 2 + dy, 0), He - ch)
        M = np.float32([[W / cw, 0, -x0 * W / cw], [0, H / ch, -y0 * H / ch]])
        a = cv2.warpAffine(ext, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
        m = cv2.warpAffine(mk, M, (W, H), flags=cv2.INTER_LINEAR)
        bl = cv2.GaussianBlur(a, (0, 0), 1.6)
        a = np.clip(a + (a - bl) * 0.55, 0, 1)            # light sharpening
        m = cv2.GaussianBlur(np.clip((m - 0.12) / 0.76, 0, 1), (0, 0), 1.5)
        a = np.clip((a - 0.02) * 1.10, 0, 1)
        return a, m

    def frame(self, fi):
        t = fi / FPS
        i = fi + 1
        z = self.zoom(t) * self.punch(t)
        bg, m = self.footage(i, t, z)
        bg = bg * self.top_shade
        # words behind him
        behind = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        if t < 1.62:
            p = spring(t, 10, 0.7)
            mw = premium_word("Money", "xb", 260, PAPER, -0.045)
            place(behind, mw, W / 2, 420 + (1 - min(p, 1)) * 60, alpha=min(1, p * 2), scale=0.94 + 0.06 * min(p, 1.05), anchor="ct")
            if t >= 0.58:
                q = expo((t - 0.58) / 0.3)
                cb = premium_word("can" if t < 1.04 else "can buy", "serif", 84, LIME)
                place(behind, cb, W / 2, 340 + (1 - q) * 12, alpha=q, anchor="ct")
        ba = np.asarray(behind).astype(np.float32) / 255
        al = ba[..., 3:4] * (1 - m[..., None])
        out = bg * (1 - al) + ba[..., :3] * al
        # graphics on top
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        self.overlay(ov, t)
        oa = np.asarray(ov).astype(np.float32) / 255
        out = out * (1 - oa[..., 3:4]) + oa[..., :3] * oa[..., 3:4]
        for b in sf.WHIP:
            d = t - b
            if -0.08 <= d < 0.12:
                k = 1 - abs(d) / (0.08 if d < 0 else 0.12)
                out = np.roll(cv2.blur(out, (int(1 + 120 * k) | 1, 1)), int(W * 0.3 * k * (-1 if d < 0 else 1)), axis=1)
        if any(0 <= t - f0 < 2 / FPS + 1e-6 for f0 in sf.FLASH):
            lum = out.mean(2)
            sil = np.clip((m > 0.5) * (lum < 0.5) + (oa[..., 3] > 0.5), 0, 1).astype(np.float32)
            sil = cv2.medianBlur((sil * 255).astype(np.uint8), 5).astype(np.float32) / 255
            out = np.dstack([sil] * 3) + (1 - sil[..., None]) * (np.array(INK) / 255)
        rng = np.random.default_rng(fi)
        out = out + rng.standard_normal(out.shape[:2]).astype(np.float32)[..., None] * 0.014
        return (np.clip(out, 0, 1) * 255).astype(np.uint8)

    KEYS = {"money", "spend", "worst", "upgrade", "happiness", "stand", "normal", "life"}

    def typed(self, ov, t, words, y=250, size=58):
        """Premium line: tight Inter Display, keywords in lime serif italic, each word rises out of a mask."""
        ims = []
        for _, w in words:
            if w.lower().strip(".,") in self.KEYS:
                ims.append((premium_word(w, "serif", int(size * 1.3), LIME), True))
            else:
                ims.append((premium_word(w, "sb", size, PAPER, -0.025), False))
        sp = int(size * 0.26)
        tw = sum(im.width for im, _ in ims) + sp * (len(ims) - 1)
        x = (W - tw) / 2
        base = y + size * 1.2
        for (st, w), (im, key) in zip(words, ims):
            q = expo((t - st) / 0.42)
            if q > 0.001:
                hh = im.height
                asc = sf.font("serif", int(size * 1.3)).getmetrics()[0] if key else sf.font("sb", size).getmetrics()[0]
                off = int((1 - q) * hh * 0.9)
                vis = im.crop((0, 0, im.width, max(1, hh - off)))
                ov.alpha_composite(vis, (int(x), int(base - asc - 4 + off)))
            x += im.width + sp

    def glow_word(self, ov, t, t0, s, y, size=250, kind="xb", grey=False):
        """Payoff word: big serif italic built letter by letter, thin lime rule, faint bloom."""
        if t < t0:
            return
        col = (176, 174, 166) if grey else (LIME if s.lower().startswith("happi") else PAPER)
        f = sf.font("serif", int(size * 1.15))
        word = premium_word(s, "serif", int(size * 1.15), col)
        x0 = (W - word.width) / 2
        lay = Image.new("RGBA", (W, word.height + 60), (0, 0, 0, 0))
        x = x0
        for k, ch in enumerate(s):
            q = expo((t - t0 - k * 0.035) / 0.5)
            cw = f.getlength(ch)
            if q > 0.001 and ch.strip():
                g = premium_word(ch, "serif", int(size * 1.15), col)
                off = int((1 - q) * g.height * 0.6)
                gl = g.crop((0, 0, g.width, max(1, g.height - off)))
                lay.alpha_composite(gl, (int(x), int(off)))
            x += cw
        if not grey:   # faint bloom + soft shadow for depth
            bloom = lay.getchannel("A").filter(ImageFilter.GaussianBlur(28)).point(lambda v: int(v * 0.30))
            bl = Image.new("RGBA", lay.size, col + (0,)); bl.putalpha(bloom)
            shade = lay.getchannel("A").filter(ImageFilter.GaussianBlur(14)).point(lambda v: int(v * 0.5))
            sh = Image.new("RGBA", lay.size, (0, 0, 0, 0)); sh.putalpha(shade)
            out = Image.new("RGBA", lay.size, (0, 0, 0, 0))
            out.alpha_composite(sh, (0, 10)); out.alpha_composite(bl); out.alpha_composite(lay)
            lay = out
        ov.alpha_composite(lay, (0, int(y)))
        # thin lime rule drawing in under the word
        r = expo((t - t0 - 0.25) / 0.6)
        if r > 0.01 and not grey:
            d = ImageDraw.Draw(ov)
            ry = y + word.height - 6
            cx = W / 2
            half = word.width * 0.42 * r
            d.rounded_rectangle((cx - half, ry, cx + half, ry + 5), 3, fill=LIME + (255,))


@lru_cache(None)
def premium_word(s, kind, size, color, track=0.0):
    f = sf.font(kind, size)
    asc, desc = f.getmetrics()
    ws = [f.getlength(c) for c in s]
    tr = track * size
    w = int(sum(ws) + tr * max(len(s) - 1, 0)) + 16
    im = Image.new("RGBA", (w, asc + desc + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = 4
    for c, cw in zip(s, ws):
        d.text((x, 4), c, font=f, fill=color + (255,))
        x += cw + tr
    bb = im.getbbox() or (0, 0, 1, 1)
    return im.crop((bb[0], 0, bb[2], im.height))


sf.Renderer = Renderer
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
            Image.fromarray(R.frame(fi)).save(os.path.join(work, f"sb_{fi:04d}.png"))
        return
    vid = os.path.join(work, "video_saas_bg.mp4")
    p = subprocess.Popen(f'ffmpeg -v error -y -f rawvideo -pix_fmt rgb24 -s {W}x{H} -r {FPS} -i - '
                         f'-c:v libx264 -preset slow -crf 15 -pix_fmt yuv420p "{vid}"', shell=True, stdin=subprocess.PIPE)
    with Pool(3, initializer=_init, initargs=(work,)) as pool:
        for buf in pool.imap(_frame, range(N), chunksize=3):
            p.stdin.write(buf)
    p.stdin.close(); p.wait()
    mix, master = os.path.join(work, "mix_sb.wav"), os.path.join(work, "master_sb.wav")
    b1.build_audio(work, mix, music, start)
    v1.loudnorm(mix, master)
    out = os.path.join(work, "AVE_Braiden_SaaS_Studio.mp4")
    v1.sh(f'ffmpeg -v error -y -i "{vid}" -i "{master}" -c:v copy -c:a aac -b:a 256k -shortest -movflags +faststart "{out}"')
    print(out)


if __name__ == "__main__":
    cmd, src, work = sys.argv[1:4]
    if cmd == "render":
        render(work, sys.argv[4] if len(sys.argv) > 4 else None, float(sys.argv[5]) if len(sys.argv) > 5 else 0.0)
    elif cmd == "stills":
        render(work, only=[int(round(float(x) * FPS)) for x in sys.argv[4:]])
