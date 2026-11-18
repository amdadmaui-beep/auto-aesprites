"""Braiden Before / After, polish pass (V2 of build_ba.py).

On top of build_ba.py:
  * footage from Real-ESRGAN upscaled frames (upscale.py -> WORK/sr/), when present;
  * the space above/below him becomes a deliberate dark studio fade, not a blurred copy of the wall;
  * filmic grade: soft S-curve, cool shadows / warm highlights, highlight halation, vignette;
  * big pale words build letter by letter, then a light sweep runs across them;
  * a small camera impact + shake when each big word lands;
  * fuller sound: risers into the big moments, low booms on the landings, a shimmer on "happiness".

Usage: python build_ba2.py render WORK FONTS_WORK [MUSIC.mp3 START]
       python build_ba2.py stills WORK FONTS_WORK 1.0 ...
"""
import math, os, subprocess, sys
from functools import lru_cache

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
import importlib.util  # noqa: E402
_spec = importlib.util.spec_from_file_location("braiden_ba", os.path.join(HERE, "build_ba.py"))
ba = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(ba)
sf, b1, v1, pv4 = ba.sf, ba.b1, ba.v1, ba.pv4
from build_v3 import expo, spring, smooth, clamp01, place  # noqa: E402

W, H, FPS, N, END = ba.W, ba.H, ba.FPS, ba.N, ba.END
LIME, INK, WHITE = ba.LIME, ba.INK, ba.WHITE
TYPE, TOP, CAP_Y = ba.TYPE, ba.TOP, ba.CAP_Y


@lru_cache(None)
def letters(s, maxw=1010):
    """Per-letter images of a pale big word, laid out and scaled like big_word()."""
    f = pv4.poppins("black", 360)
    full = _orig_big(s, "fill", 10 ** 6)
    k = min(1.0, maxw / full.width)
    out, x = [], 0.0
    lw, tw, _, _ = f.getbbox(s)
    for ch in s:
        g = pv4.grad(pv4.word_img(ch, "black", 360, WHITE), ba.PALE_T, (232, 244, 186), ba.PALE_B)
        l, tc, _, _ = f.getbbox(ch)
        g = g.resize((max(1, int(g.width * k)), max(1, int(g.height * k))), Image.LANCZOS)
        out.append((g, (x + l - lw) * k, (tc - tw) * k))
        x += f.getlength(ch)
    return out, int(full.width * k), int(full.height * k)


class Edit(ba.Edit):
    def __init__(self, work):
        super().__init__(work)
        self.sr_dir = os.path.join(work, "sr")
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        self.vig = (1 - 0.30 * np.clip(((xx - W / 2) / (W * 0.72)) ** 2 + ((yy - H * 0.52) / (H * 0.62)) ** 2, 0, 1))[..., None]
        x = np.linspace(0, 1, 256, dtype=np.float32)
        self.curve = (x * 0.6 + (x * x * (3 - 2 * x)) * 0.4)        # gentle filmic S

    def hr(self, i):
        p = os.path.join(self.sr_dir, f"{min(max(i, 1), N):04d}.jpg")
        if os.path.exists(p):
            im = cv2.cvtColor(cv2.imread(p), cv2.COLOR_BGR2RGB)
        else:
            im = cv2.resize(np.asarray(self.raw(i)), (1440, 808), interpolation=cv2.INTER_CUBIC)
        return im.astype(np.float32) / 255

    def punch(self, t):
        k = ba.Edit.punch(self, t)
        for on, *_ in TYPE:       # impact when each big word lands
            d = t - (on + 0.30)
            if 0 <= d < 0.5:
                k += 0.018 * math.exp(-d * 9)
        return k

    def footage(self, i, t, z):
        S = 1440 / 1080
        k = next(n for n, (a, b) in enumerate(sf.SHOTS) if a <= t < b or n == len(sf.SHOTS) - 1)
        _, cx, top, bot = self.shot_geo[k]
        cx, top, bot = cx * S, top * S, bot * S
        T, Bx = int(self.TOP_EXT * S), int(self.BOT_EXT * S)
        src = self.hr(i)
        hh, ww = src.shape[:2]
        mk = cv2.resize(np.asarray(self.mask(i)).astype(np.float32) / 255, (ww, hh))
        soft_bg = cv2.GaussianBlur(src, (0, 0), 2.6)
        src = src * mk[..., None] + soft_bg * (1 - mk[..., None])
        # dark studio fade above and below him
        topx = cv2.GaussianBlur(cv2.resize(src[:int(120 * S)], (ww, T + 100)), (0, 0), 30)
        g = np.linspace(0.06, 0.8, T + 100, dtype=np.float32)[:, None, None] ** 1.6
        topx = topx * g
        botx = cv2.GaussianBlur(cv2.resize(src[-int(60 * S):], (ww, Bx + 60)), (0, 0), 20)
        botx = botx * np.linspace(0.8, 0.1, Bx + 60, dtype=np.float32)[:, None, None]
        ext = np.concatenate([topx[:T], src, botx[60:]], 0)
        yy = np.arange(100, dtype=np.float32)[:, None, None] / 100
        ext[T:T + 100] = topx[T:T + 100] * (1 - yy) + src[:100] * yy
        mke = np.concatenate([np.zeros((T, ww), np.float32), mk, np.zeros((Bx, ww), np.float32)], 0)
        He = hh + T + Bx
        ch = He / z
        cw = ch * W / H
        head = T + top + 0.15 * (bot - top)
        cy = He / 2 + (head - He / 2) * clamp01((z - 1) / 0.3)
        dx = (3 * math.sin(t * 1.3) + 1.5 * math.sin(t * 2.9)) * S
        dy = 2 * math.sin(t * 1.7 + 1) * S
        for on, *_ in TYPE:       # landing shake
            d = t - (on + 0.30)
            if 0 <= d < 0.4:
                e = math.exp(-d * 10) * 6 * S
                dx += e * math.sin(d * 70); dy += e * math.cos(d * 55)
        x0 = min(max(cx - cw / 2 + dx, 0), ww - cw)
        y0 = min(max(cy - ch / 2 + dy, 0), He - ch)
        M = np.float32([[W / cw, 0, -x0 * W / cw], [0, H / ch, -y0 * H / ch]])
        a = cv2.warpAffine(ext, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
        m = cv2.warpAffine(mke, M, (W, H), flags=cv2.INTER_LINEAR)
        m = cv2.GaussianBlur(np.clip((m - 0.12) / 0.76, 0, 1), (0, 0), 1.5)
        # filmic grade
        a = np.clip((a - 0.012) * 1.06, 0, 1)
        a = self.curve[(a * 255).astype(np.uint8)]
        lum = a.mean(2, keepdims=True)
        a = a + (1 - lum) * np.array([-0.012, 0.0, 0.018]) + lum * np.array([0.022, 0.010, -0.014])
        hi = cv2.GaussianBlur(np.clip((lum[..., 0] - 0.62) / 0.38, 0, 1), (0, 0), 16)
        a = a + hi[..., None] * np.array([0.14, 0.07, 0.03])
        a = np.clip(a, 0, 1) * self.vig
        return a, m

    def frame(self, fi):
        # draw the frame with build_ba's logic, then lay the letter-build + light sweep over the pale words
        t = fi / FPS
        self._t = t
        return super().frame(fi)


# --- swap the pale big words for a letter-by-letter build with a light sweep ---------------------
_orig_big = ba.big_word


def big_word_animated(s, style="fill", maxw=1010):
    t = getattr(_CURRENT, "t", None)
    if style != "fill" or t is None:
        return _orig_big(s, style, maxw)
    on = next((e[0] for e in TYPE if e[4] == s and e[0] - 0.12 <= t < e[1]), None)
    if on is None:
        return _orig_big(s, style, maxw)
    ls, w, h = letters(s, maxw)
    im = Image.new("RGBA", (w + 20, h + 20), (0, 0, 0, 0))
    for k, (g, x, y) in enumerate(ls):
        q = expo((t - on - k * 0.032) / 0.45)
        if q <= 0.001:
            continue
        off = int((1 - q) * g.height * 0.5)
        part = g.crop((0, 0, g.width, max(1, g.height - off)))
        if q < 0.999:
            part = part.copy(); part.putalpha(part.getchannel("A").point(lambda v, q=q: int(v * min(1, q * 1.4))))
        im.alpha_composite(part, (max(0, int(x)), int(y) + off))
    # light sweep once the word has landed
    d = t - on - 0.45
    if 0 <= d < 0.75:
        sx = -200 + (w + 400) * smooth(d / 0.75)
        band = Image.new("L", im.size, 0)
        ImageDraw.Draw(band).polygon([(sx, 0), (sx + 70, 0), (sx - 40, h), (sx - 110, h)], fill=170)
        band = band.filter(ImageFilter.GaussianBlur(14))
        a = np.minimum(np.asarray(band), np.asarray(im.getchannel("A")))
        gl = Image.new("RGBA", im.size, WHITE + (0,)); gl.putalpha(Image.fromarray(a))
        im.alpha_composite(gl)
    return im


class _Cur:
    t = None


_CURRENT = _Cur()
ba.big_word = big_word_animated


class Page(ba.Page):
    def __init__(self, work, fonts_work):
        super().__init__(work, fonts_work)
        self.edit = Edit(work)

    def frame(self, fi):
        _CURRENT.t = fi / FPS
        return super().frame(fi)


# --- fuller sound design ------------------------------------------------------------------------
_orig_make = v1.make_sfx


def make_sfx(kind, rng):
    SR = v1.SR
    if kind == "riser":
        n = int(0.9 * SR); t = np.arange(n) / SR
        f = 300 + 2600 * (t / 0.9) ** 2
        noise = v1.bandpass(rng.standard_normal(n), 800, 7000)
        x = (0.5 * noise + 0.3 * np.sin(2 * np.pi * np.cumsum(f) / SR)) * (t / 0.9) ** 2.2
        return v1.lowpass(x, 6000) * 0.5, 0.9
    if kind == "boom":
        n = int(0.9 * SR); t = np.arange(n) / SR
        f = 42 + 50 * np.exp(-t / 0.06)
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.28) * 1.1, 0.0
    if kind == "shimmer":
        n = int(1.4 * SR); t = np.arange(n) / SR
        x = sum(np.sin(2 * np.pi * fr * t) for fr in (1318, 1760, 2637)) / 3 * (1 + 0.3 * np.sin(2 * np.pi * 7 * t))
        return x * np.minimum(t / 0.05, 1) * np.exp(-t / 0.6) * 0.35, 0.0
    return _orig_make(kind, rng)


v1.make_sfx = make_sfx
SFX = ([(t, "whoosh") for t in (1.30, 3.13, 5.52, 8.77, 9.0, 10.54, 11.08, 11.62, 13.4)]
       + [(t + 0.05, "air") for t, *_ in TYPE]
       + [(t + 0.30, "boom") for t, *_ in TYPE if t > 0]
       + [(7.82, "riser"), (15.98, "riser"), (15.98, "shimmer"), (1.30, "riser")]
       + [(t, "bloop") for t in (5.80, 6.06, 9.25)]
       + [(t, "flash") for t in sf.FLASH])
b1.SFX[:] = SFX

P = None


def _init(work, fonts_work):
    global P
    P = Page(work, fonts_work)


def _frame(fi):
    return P.frame(fi).tobytes()


def render(work, fonts_work, music=None, start=0.0, only=None):
    from multiprocessing import Pool
    if only is not None:
        _init(work, fonts_work)
        for fi in only:
            Image.fromarray(P.frame(fi)).save(os.path.join(work, f"ba2_{fi:04d}.png"))
        return
    vid = os.path.join(work, "video_ba2.mp4")
    p = subprocess.Popen(f'ffmpeg -v error -y -f rawvideo -pix_fmt rgb24 -s {W}x{H} -r {FPS} -i - '
                         f'-c:v libx264 -preset slow -crf 14 -pix_fmt yuv420p "{vid}"', shell=True, stdin=subprocess.PIPE)
    with Pool(3, initializer=_init, initargs=(work, fonts_work)) as pool:
        for buf in pool.imap(_frame, range(N), chunksize=3):
            p.stdin.write(buf)
    p.stdin.close(); p.wait()
    mix, master = os.path.join(work, "mix_ba2.wav"), os.path.join(work, "master_ba2.wav")
    b1.build_audio(work, mix, music, start)
    v1.loudnorm(mix, master)
    out = os.path.join(work, "AVE_Braiden_Before_After_V2.mp4")
    v1.sh(f'ffmpeg -v error -y -i "{vid}" -i "{master}" -c:v copy -c:a aac -b:a 256k -shortest -movflags +faststart "{out}"')
    print(out)


if __name__ == "__main__":
    cmd, work, fonts_work = sys.argv[1:4]
    if cmd == "render":
        render(work, fonts_work, sys.argv[4] if len(sys.argv) > 4 else None, float(sys.argv[5]) if len(sys.argv) > 5 else 0.0)
    elif cmd == "stills":
        render(work, fonts_work, only=[int(round(float(x) * FPS)) for x in sys.argv[4:]])
