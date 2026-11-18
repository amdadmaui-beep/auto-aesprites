"""AVE Studio re-edit of Braiden Shaw's "Money can buy happiness" clip.

Format: his raw clip on top, our edit underneath (1080x1920, 30 fps).
Only his raw footage and voice are taken from the source reel; the titles,
graphics, cut-away cards, sound and layout are ours. The source reel's
bottom card (the other editor's handle) and its middle edit are not used.

Usage:
    python build.py prep   SOURCE.mp4 WORK      # raw footage, cut-outs, voice
    python build.py render SOURCE.mp4 WORK [MUSIC.mp3 START]
    python build.py stills SOURCE.mp4 WORK 1.0 6.9 ...
"""
import math, os, subprocess, sys
from functools import lru_cache

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "before-after-reel"))
import build as v1                      # noqa: E402  (sfx synth, loudnorm, prep helpers)
from build_v3 import expo, spring, smooth, clamp01, place  # noqa: E402

W, H, FPS = 1080, 1920, 30
PW, PH = 1080, 608                       # each 16:9 panel
RAW_Y, EDIT_Y = 352, 1040                # panel tops
INK, PAPER, LIME = (14, 14, 14), (243, 242, 238), (200, 255, 46)
RAISED = (28, 27, 25)
MUTED = (138, 135, 127)
FONTS = os.path.join(ROOT, "ave-promo", "film", "fonts")

# raw shots in the source: wide 0-3.13, close 3.13-8.77, wide 8.77-end
N = 527
END = N / FPS

# ---- timeline (from the transcript) -----------------------------------------
CUTAWAY = [(10.54, 11.08, "CAR", "01"), (11.08, 11.62, "HOUSE", "02"), (11.62, 12.24, "VACATION", "03")]
SFX = ([(t, "whoosh") for t in (10.54, 11.08, 11.62, 12.24)]
       + [(0.30, "flash"), (6.48, "thock"), (7.82, "bloop"), (8.92, "bloop"), (10.14, "ding"),
          (13.62, "air"), (15.98, "bloop")])


@lru_cache(None)
def font(kind, size):
    files = {"xb": "InterDisplay-ExtraBold.otf", "b": "InterDisplay-Bold.otf", "sb": "InterDisplay-SemiBold.otf",
             "md": "InterDisplay-Medium.otf", "serif": "InstrumentSerif-italic-400.woff2",
             "mono": "JetBrainsMono-normal-500.woff2"}
    return ImageFont.truetype(os.path.join(FONTS, files[kind]), size)


@lru_cache(None)
def txt(s, kind, size, color, track=0):
    f = font(kind, size)
    if track:
        ws = [f.getlength(c) for c in s]
        im = Image.new("RGBA", (int(sum(ws) + track * len(s)) + 20, int(size * 1.5)), (0, 0, 0, 0))
        d = ImageDraw.Draw(im); x = 4
        for c, cw in zip(s, ws):
            d.text((x, 4), c, font=f, fill=color + (255,)); x += cw + track
    else:
        l, t, r, b = f.getbbox(s)
        im = Image.new("RGBA", (r - l + 12, b - t + 12), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((6 - l, 6 - t), s, font=f, fill=color + (255,))
    return im.crop(im.getbbox() or (0, 0, 1, 1))


@lru_cache(None)
def word_img(s, kind, size, color):
    """A word on a fixed baseline box (bottom = baseline + descender), so words line up."""
    f = font(kind, size)
    asc, desc = f.getmetrics()
    w = int(f.getlength(s)) + 8
    im = Image.new("RGBA", (w, asc + desc), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((2, 0), s, font=f, fill=color + (255,))
    bb = im.getbbox() or (0, 0, 1, 1)
    return im.crop((bb[0], 0, bb[2], asc + desc))


def rounded(w, h, r, ss=4):
    m = Image.new("L", (w * ss, h * ss), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w * ss - 1, h * ss - 1), r * ss, fill=255)
    return m.resize((w, h), Image.LANCZOS)


# ===========================================================================
def prep(src, work):
    raw = os.path.join(work, "raw"); os.makedirs(raw, exist_ok=True)
    if not os.listdir(raw):
        v1.sh(f'ffmpeg -v error -i "{src}" -vf "crop=720:404:0:1,scale={PW}:{PH}:flags=lanczos,'
              f'unsharp=5:5:0.4:5:5:0" -q:v 2 "{raw}/%04d.jpg"')
    voc = os.path.join(work, "voice.wav")
    if not os.path.exists(voc):
        import soundfile as sf, torch
        from demucs.pretrained import get_model
        from demucs.apply import apply_model
        tmp = os.path.join(work, "a44.wav")
        v1.sh(f'ffmpeg -v error -y -i "{src}" -vn -ar 44100 -ac 2 "{tmp}"')
        m = get_model("htdemucs_ft"); m.eval()
        a, sr = sf.read(tmp, dtype="float32"); x = torch.tensor(a.T)[None]; r = x.mean(1, keepdim=True)
        with torch.no_grad():
            o = apply_model(m, (x - r.mean()) / r.std(), shifts=1, split=True, overlap=0.25)[0]
        sf.write(voc, (o * r.std() + r.mean())[m.sources.index("vocals")].numpy().T, sr)
    # cut-outs for the opening title that sits behind him (0 - 3.13 s)
    mk = os.path.join(work, "mask"); os.makedirs(mk, exist_ok=True)
    from rembg import remove, new_session
    sess = None
    for i in range(1, 96):
        o = os.path.join(mk, f"{i:04d}.png")
        if not os.path.exists(o):
            sess = sess or new_session("u2net_human_seg")
            remove(Image.open(os.path.join(raw, f"{i:04d}.jpg")).convert("RGB"), session=sess, only_mask=True).save(o)


# ===========================================================================
class Renderer:
    def __init__(self, work):
        self.work = work
        self.page = self.build_page()
        self.pmask = rounded(PW - 64, PH - 36, 22)

    def raw(self, i):
        i = min(max(i, 1), N)
        return Image.open(os.path.join(self.work, "raw", f"{i:04d}.jpg")).convert("RGB")

    def build_page(self):
        img = Image.new("RGBA", (W, H), INK + (255,))
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        g = np.exp(-(((xx - 900) / 700) ** 2 + ((yy - 120) / 500) ** 2)) * 0.10
        arr = np.array(INK, np.float32) * (1 - g[..., None]) + np.array(LIME, np.float32) * g[..., None]
        img = Image.fromarray(arr.astype(np.uint8)).convert("RGBA")
        d = ImageDraw.Draw(img)
        wm = Image.open(os.path.join(ROOT, "brand", "logos", "ave-wordmark-paper.png")).convert("RGBA")
        wm = wm.resize((int(wm.width * 54 / wm.height), 54), Image.LANCZOS)
        img.alpha_composite(wm, ((W - wm.width) // 2, 150))
        st = txt("STUDIO", "mono", 22, MUTED, track=9)
        img.alpha_composite(st, ((W - st.width) // 2, 222))
        for y, label, fill, fg in ((RAW_Y - 66, "RAW", RAISED, PAPER), (EDIT_Y - 66, "EDITED BY AVE", LIME, INK)):
            t = txt(label, "mono", 24, fg, track=4)
            w = t.width + 46
            d.rounded_rectangle((32, y, 32 + w, y + 46), 23, fill=fill + (255,))
            img.alpha_composite(t, (32 + 23, y + (46 - t.height) // 2))
        cr = txt("Original video: @braidenshaw", "md", 30, MUTED)
        img.alpha_composite(cr, ((W - cr.width) // 2, 1712))
        return img

    # ---- edit panel ----------------------------------------------------------
    def shot(self, i, t):
        """Raw footage with our framing: slow push-ins, a punch-in on the close shot."""
        im = self.raw(i)
        if t < 3.13:
            k, cx, cy = 1.06 + 0.05 * smooth(t / 3.13), 0.42, 0.42
        elif t < 8.77:
            k = 1.0 + 0.04 * smooth((t - 3.13) / 5.6) + (0.10 * expo((t - 6.48) / 0.5) if t >= 6.48 else 0)
            cx, cy = 0.36, 0.40
        else:
            k, cx, cy = 1.08 + 0.04 * smooth((t - 8.77) / 8.8), 0.48, 0.42
        w, h = im.size
        cw, ch = w / k, h / k
        x0 = min(max(cx * w - cw * cx, 0), w - cw); y0 = min(max(cy * h - ch * cy, 0), h - ch)
        return im.resize((PW, PH), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))

    def grade(self, im, t):
        a = np.asarray(im).astype(np.float32) / 255
        a = np.clip((a - 0.03) * 1.08, 0, 1)
        lum = a.mean(2, keepdims=True)
        sat = 1.08
        if t >= 13.3:   # "that life just feels normal": colour drains out
            sat = 1.08 - 0.9 * smooth((t - 13.3) / 1.0) + 0.9 * smooth((t - 15.9) / 0.6)
        a = lum + (a - lum) * sat
        # cool shadows, warm highlights, soft vignette
        a[..., 2] += (0.5 - lum[..., 0]) * 0.04
        yy, xx = np.mgrid[0:PH, 0:PW].astype(np.float32)
        v = 1 - 0.35 * np.clip(((xx - PW / 2) / (PW * 0.62)) ** 2 + ((yy - PH / 2) / (PH * 0.75)) ** 2, 0, 1)
        return Image.fromarray((np.clip(a * v[..., None], 0, 1) * 255).astype(np.uint8)).convert("RGBA")

    def edit(self, i, t):
        if any(a <= t < b for a, b, _, _ in CUTAWAY):
            return self.cutaway(t)
        base = self.grade(self.shot(i, t), t)
        # opening: "Money can buy / Happiness", the payoff word behind him
        if t < 3.13:
            pm = expo((t - 0.0) / 0.5)
            ph = expo((t - 1.30) / 0.7)
            lay = Image.new("RGBA", (PW, PH), (0, 0, 0, 0))
            hp = txt("Happiness", "serif", 200, LIME)
            place(lay, hp, PW * 0.52, 150 + (1 - ph) * 50, alpha=ph, blur=(1 - ph) * 10, anchor="ct")
            m = Image.open(os.path.join(self.work, "mask", f"{min(i, 95):04d}.png")).convert("L")
            m = self.match_shot(m, t)
            lay_a = np.asarray(lay).astype(np.float32)
            lay_a[..., 3] *= 1 - np.asarray(m).astype(np.float32) / 255
            base.alpha_composite(Image.fromarray(lay_a.astype(np.uint8)))
            mc = txt("Money can buy", "sb", 54, PAPER)
            place(base, mc, PW * 0.52, 100 + (1 - pm) * 20, alpha=pm, blur=(1 - pm) * 5, anchor="ct")
            if t >= 1.82:
                self.caption(base, t, [(1.82, "and"), (2.04, "I'm"), (2.22, "gonna"), (2.26, "stand"), (2.58, "by"), (2.78, "that.")])
        elif t < 8.77:
            if t < 6.40:
                self.caption(base, t, [(3.04, "But"), (3.34, "I"), (3.44, "think"), (3.54, "most"), (3.88, "of"), (4.08, "us")]
                             if t < 4.20 else
                             [(4.22, "get"), (4.40, "a"), (4.52, "little"), (4.64, "bit"), (4.80, "of"), (4.90, "money,")]
                             if t < 5.10 else
                             [(5.12, "and"), (5.32, "then"), (5.42, "we"), (5.52, "spend"), (5.78, "it"), (5.92, "on"), (6.06, "things")])
            else:
                self.top_band(base, t)
        elif t < 10.54:
            self.money_pill(base, t)
        elif t >= 12.24:
            if t < 14.40:
                p = expo((t - 13.62) / 0.6)
                if t >= 12.24:
                    self.caption(base, t, [(12.24, "Eventually"), (12.76, "that"), (13.08, "life"), (13.36, "just"), (13.62, "feels")],
                                 y=PH - 150)
                if t >= 13.62:
                    nm = txt("normal.", "serif", 150, PAPER)
                    place(base, nm, PW / 2, PH - 150 + (1 - p) * 30, alpha=p, blur=(1 - p) * 8, anchor="ct")
            else:
                self.caption(base, t, [(14.42, "and"), (14.70, "so"), (14.86, "you"), (15.02, "no"), (15.22, "longer"), (15.44, "have"),
                                       (15.78, "that")] if t < 15.98 else
                             [(15.98, "*happiness"), (16.46, "that"), (16.76, "can"), (16.92, "come"), (17.12, "from"), (17.30, "it.")])
        return base

    def match_shot(self, m, t):
        """Apply the same framing as shot() to the cut-out mask (opening shot only)."""
        k, cx, cy = 1.06 + 0.05 * smooth(t / 3.13), 0.42, 0.42
        w, h = m.size
        cw, ch = w / k, h / k
        x0 = min(max(cx * w - cw * cx, 0), w - cw); y0 = min(max(cy * h - ch * cy, 0), h - ch)
        return m.resize((PW, PH), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch)).filter(ImageFilter.GaussianBlur(1.2))

    def caption(self, base, t, words, y=None):
        """Word-by-word caption; '*word' is the payoff word (lime serif)."""
        y = PH - 40 if y is None else y
        ims = []
        for st, wd in words:
            if wd.startswith("*"):
                ims.append((st, word_img(wd[1:], "serif", 76, LIME), True))
            else:
                ims.append((st, word_img(wd, "xb", 56, PAPER), False))
        sp = 16
        tw = sum(im.width for _, im, _ in ims) + sp * (len(ims) - 1)
        x = (PW - tw) / 2
        # soft shade so the words read on any frame
        shade = Image.new("RGBA", (PW, PH), (0, 0, 0, 0))
        sa = np.zeros((PH, PW), np.float32)
        yy = np.arange(PH)[:, None]
        sa[:] = np.clip((yy - (y - 140)) / 220, 0, 1) * 150
        shade.putalpha(Image.fromarray(sa.astype(np.uint8)))
        base.alpha_composite(shade)
        for st, im, serif in ims:
            p = expo((t - st + 0.04) / 0.35)
            if p > 0:
                place(base, im, x, y - im.height + (1 - p) * 22 + (6 if serif else 0),
                      alpha=min(1, p * 1.5), blur=(1 - p) * 5)
            x += im.width + sp

    def top_band(self, base, t):
        """'that are the worst at buying / Happiness' on a lime band sliding down."""
        p = expo((t - 6.48) / 0.55)
        bh = 170
        y = -bh + bh * p
        band = Image.new("RGBA", (PW, bh), LIME + (255,))
        a = txt("that are the worst at buying", "sb", 40, INK)
        band.alpha_composite(a, (PW - a.width - 60, 26))
        if t >= 7.82:
            q = expo((t - 7.82) / 0.5)
            hp = txt("Happiness", "serif", 104, INK)
            lay = Image.new("RGBA", band.size, (0, 0, 0, 0))
            place(lay, hp, PW - hp.width - 60 + (1 - q) * 40, 66, alpha=q, blur=(1 - q) * 6)
            band.alpha_composite(lay)
        place(base, band, 0, y)

    def money_pill(self, base, t):
        """'you make a little more money' -> a counter that ticks up; 'so you upgrade'."""
        p = spring(t - 8.92, 12, 0.72)
        val = 4200 + int((7800 - 4200) * smooth((t - 9.3) / 0.6))
        s = f"${val:,}"
        tag = txt("MONTHLY INCOME", "mono", 20, MUTED, track=4)
        num = txt(s, "xb", 66, PAPER)
        w, h = 400, 158
        card = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(card)
        d.rounded_rectangle((0, 0, w - 1, h - 1), 26, fill=(14, 14, 14, 210), outline=(255, 255, 255, 40), width=2)
        card.alpha_composite(tag, (28, 24))
        card.alpha_composite(num, (28, 70))
        if t >= 9.3:
            q = expo((t - 9.3) / 0.4)
            ar = txt("+86%", "sb", 30, INK)
            pw_ = ar.width + 28
            d.rounded_rectangle((w - pw_ - 24, 78, w - 24, 118), 20, fill=LIME + (int(255 * q),))
            card.alpha_composite(ar, (w - pw_ - 10, 84))
        place(base, card, 56 - (1 - p) * 60, 70, alpha=min(1, p * 1.4), blur=(1 - clamp01(p)) * 5)
        if t >= 10.14:
            q = expo((t - 10.14) / 0.35)
            up = txt("so you upgrade", "xb", 56, PAPER)
            place(base, up, PW / 2, PH - 120 + (1 - q) * 20, alpha=q, blur=(1 - q) * 5, anchor="ct")

    def cutaway(self, t):
        """Our own cut-away cards for 'the car, the house, or the vacation'."""
        a, b, word, n = next(c for c in CUTAWAY if c[0] <= t < c[1])
        img = Image.new("RGBA", (PW, PH), INK + (255,))
        yy, xx = np.mgrid[0:PH, 0:PW].astype(np.float32)
        g = np.exp(-(((xx - PW * 0.7) / 500) ** 2 + ((yy - PH * 0.3) / 300) ** 2)) * 0.28
        arr = np.array(INK, np.float32) * (1 - g[..., None]) + np.array(LIME, np.float32) * g[..., None]
        img = Image.fromarray(arr.astype(np.uint8)).convert("RGBA")
        p = expo((t - a) / 0.4)
        big = txt(word, "xb", 230, PAPER)
        if big.width > PW - 120:
            big = big.resize((PW - 120, int(big.height * (PW - 120) / big.width)), Image.LANCZOS)
        # outline copy behind, filled copy wipes in
        ol = big.filter(ImageFilter.MaxFilter(5))
        ol_a = np.asarray(ol.getchannel("A")).astype(np.float32) - np.asarray(big.getchannel("A")).astype(np.float32) * 0.0
        out = Image.new("RGBA", big.size, PAPER + (0,))
        out.putalpha(Image.fromarray((np.clip(ol_a - np.asarray(big.getchannel("A")), 0, 255) * 0.6).astype(np.uint8)))
        x, y = (PW - big.width) / 2, (PH - big.height) / 2 + 30
        place(img, out, x, y + (1 - p) * 30)
        fa = np.asarray(big.getchannel("A")).astype(np.float32)
        edge = p * (big.width + 80) - 80
        fa *= np.clip((edge - np.arange(big.width)[None, :]) / 80 + 1, 0, 1)
        fill = big.copy(); fill.putalpha(Image.fromarray(fa.astype(np.uint8)))
        place(img, fill, x, y + (1 - p) * 30)
        lab = txt(f"UPGRADE {n} / 03", "mono", 24, LIME, track=6)
        place(img, lab, PW / 2, y - 60 + (1 - p) * 14, alpha=p, anchor="ct")
        bar_w = 360
        d = ImageDraw.Draw(img)
        bx = (PW - bar_w) / 2
        d.rounded_rectangle((bx, PH - 86, bx + bar_w, PH - 78), 4, fill=(60, 60, 56, 255))
        lvl = (int(n) - 1 + expo((t - a) / 0.45)) / 3
        d.rounded_rectangle((bx, PH - 86, bx + bar_w * lvl, PH - 78), 4, fill=LIME + (255,))
        return img

    # ---- frame -------------------------------------------------------------------
    def frame(self, fi):
        t = fi / FPS
        i = fi + 1
        page = self.page.copy()
        pw, ph = PW - 64, PH - 36
        raw = self.raw(i).resize((pw, ph), Image.LANCZOS).convert("RGBA"); raw.putalpha(self.pmask)
        page.alpha_composite(raw, (32, RAW_Y))
        ed = self.edit(i, t)
        # whip between the cut-aways and the speaker
        for b in (10.54, 11.08, 11.62, 12.24):
            dt = t - b
            if -0.1 <= dt < 0.12:
                k = 1 - abs(dt) / 0.12
                arr = np.asarray(ed.convert("RGB"))
                arr = cv2.blur(arr, (int(1 + 60 * k) | 1, 1))
                ed = Image.fromarray(arr).convert("RGBA")
        ed = ed.resize((pw, ph), Image.LANCZOS); ed.putalpha(self.pmask)
        page.alpha_composite(ed, (32, EDIT_Y))
        return np.asarray(page.convert("RGB"))


# ===========================================================================
SR = 48000


def build_audio(work, out_wav, music=None, start=0.0):
    import soundfile as sf
    from scipy.signal import butter, sosfilt, resample_poly
    n = int(END * SR)
    v, sr = sf.read(os.path.join(work, "voice.wav"), dtype="float32")
    v = v.mean(1) if v.ndim > 1 else v
    v = resample_poly(v, SR, sr).astype(np.float32) if sr != SR else v
    v = np.pad(v, (0, max(0, n - len(v))))[:n]
    v = sosfilt(butter(2, 75, "high", fs=SR, output="sos"), v)
    v = v / (np.abs(v).max() + 1e-9) * 0.7
    fx = np.zeros(n); rng = np.random.default_rng(3)
    for t0, kind in SFX:
        x, pre = v1.make_sfx(kind, rng)
        s = int((t0 - pre) * SR)
        if s < 0:
            x = x[-s:]; s = 0
        e = min(n, s + len(x)); fx[s:e] += x[:e - s]
    mix = np.stack([v + fx * 0.12] * 2, 1)
    if music:
        raw = subprocess.run(f'ffmpeg -v error -ss {start} -i "{music}" -t {END + 0.5} -ac 2 -ar {SR} -f f32le -',
                             shell=True, check=True, capture_output=True).stdout
        mu = np.frombuffer(raw, np.float32).reshape(-1, 2)
        mu = np.pad(mu, ((0, max(0, n - len(mu))), (0, 0)))[:n].copy()
        tt = np.arange(n) / SR
        mu *= np.clip(tt / 0.03, 0, 1)[:, None] * np.clip((END - tt) / 1.2, 0, 1)[:, None]
        mu = mu / (np.sqrt(np.mean(mu ** 2)) + 1e-9) * np.sqrt(np.mean(v ** 2)) * 0.28
        env = sosfilt(butter(1, 6, "low", fs=SR, output="sos"), np.abs(v))
        env = env / (np.percentile(env, 95) + 1e-9)
        mu *= sosfilt(butter(1, 3, "low", fs=SR, output="sos"), 10 ** (-5 * np.clip(env, 0, 1) / 20))[:, None]
        mix = mix + mu
    sf.write(out_wav, mix.astype(np.float32), SR)


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
            Image.fromarray(R.frame(fi)).save(os.path.join(work, f"s_{fi:04d}.png"))
        return
    vid = os.path.join(work, "video.mp4")
    p = subprocess.Popen(f'ffmpeg -v error -y -f rawvideo -pix_fmt rgb24 -s {W}x{H} -r {FPS} -i - '
                         f'-c:v libx264 -preset slow -crf 15 -pix_fmt yuv420p "{vid}"', shell=True, stdin=subprocess.PIPE)
    with Pool(3, initializer=_init, initargs=(work,)) as pool:
        for buf in pool.imap(_frame, range(N), chunksize=4):
            p.stdin.write(buf)
    p.stdin.close(); p.wait()
    mix, master = os.path.join(work, "mix.wav"), os.path.join(work, "master.wav")
    build_audio(work, mix, music, start)
    v1.loudnorm(mix, master)
    out = os.path.join(work, "AVE_Braiden_Reedit.mp4")
    v1.sh(f'ffmpeg -v error -y -i "{vid}" -i "{master}" -c:v copy -c:a aac -b:a 256k -shortest -movflags +faststart "{out}"')
    print(out)


if __name__ == "__main__":
    cmd, src, work = sys.argv[1:4]
    if cmd == "prep":
        prep(src, work)
    elif cmd == "render":
        render(work, sys.argv[4] if len(sys.argv) > 4 else None, float(sys.argv[5]) if len(sys.argv) > 5 else 0.0)
    elif cmd == "stills":
        render(work, only=[int(round(float(x) * FPS)) for x in sys.argv[4:]])
