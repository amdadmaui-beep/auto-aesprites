"""Braiden Shaw · Before / After of our SaaS-style edit, heavy-type pass.

Before: his raw clip in black and white. After: our SaaS-style edit (real studio,
3D cards, flashes, whips) retyped in the heavy style the user referenced:
Poppins Black lowercase words with a lime gradient behind him, light kickers on
their corner, bold-italic add-ons, one-word captions with corner brackets.
The two reels the user sent were references only (Before/After layout and the
type style); none of their footage or graphics is used.

Needs: WORK (Braiden: raw/, mask/, voice.wav, words.json, broll/) and FONTS_WORK
(a dir with fonts/Poppins-*.ttf, e.g. the before-after-reel work dir).
Usage: python build_ba.py render WORK FONTS_WORK [MUSIC.mp3 START]
       python build_ba.py stills WORK FONTS_WORK 1.0 ...
"""
import json, math, os, subprocess, sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
import importlib.util  # noqa: E402
_spec = importlib.util.spec_from_file_location("braiden_saas_bg", os.path.join(HERE, "build_saas_bg.py"))
bg = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(bg)
sf, b1, v1 = bg.sf, bg.b1, bg.v1
import build_v2 as pv2      # before-after-reel page + palette (on sys.path via build.py)  # noqa: E402
import build_v4 as pv4      # Poppins type helpers  # noqa: E402
from build_v3 import expo, spring, smooth, clamp01, place  # noqa: E402

W, H, FPS, N, END = sf.W, sf.H, sf.FPS, sf.N, sf.END
INK, PAPER, LIME = sf.INK, sf.PAPER, sf.LIME
WHITE = (255, 255, 255)
CARD, BEFORE = pv2.CARD, pv2.BEFORE

# (start, end, kicker, big, add-on, add-on time) — 1080x1920 edit coordinates
TYPE = [
    (0.00, 1.30, None, "money", None, None),
    (3.40, 4.22, "most of", "us", None, None),
    (4.80, 5.12, "a little bit of", "money", None, None),
    (7.10, 8.77, "the worst at", "buying", "happiness", 7.82),
    (10.14, 10.54, "so you", "upgrade", None, None),
    (13.55, 14.42, "just feels", "normal", None, None),
    (15.98, END, "no longer", "happiness", "that can come from it", 16.46),
]
BRACKETS = [(1.82, 3.04), (8.42, 9.86), (14.42, 15.9)]
TOP = 470
CAP_Y = 1330


def big_word(s, maxw=980):
    im = pv4.grad(pv4.word_img(s, "black", 330, WHITE))
    if im.width > maxw:
        im = im.resize((maxw, int(im.height * maxw / im.width)), Image.LANCZOS)
    return im


class Edit(bg.Renderer):
    """The After: SaaS edit with the heavy type system."""

    def __init__(self, work):
        super().__init__(work)
        self.words = json.load(open(os.path.join(work, "words.json")))

    def whip(self, t, on, off):
        p = expo((t - on) / 0.38)
        x, blur, a = (1 - p) * 200, (1 - p) * 130, min(1, p * 1.6)
        if off < END - 0.01 and t > off - 0.16:
            q = smooth((t - (off - 0.16)) / 0.16)
            x -= q * 220; blur += q * 130; a *= 1 - q
        return x, blur, a

    def overlay(self, ov, t):
        """3D cards only (the words are drawn separately)."""
        w = self.work
        if 1.30 <= t < 3.4:
            self.fly(ov, sf.gloss_tile("dollar", 360), t, 1.30, W * 0.33, 560, ry=18, rz=-8, glow_c=LIME, exit_t=3.04)
            self.fly(ov, sf.photo_card("car", "Happiness", "money can buy it?", w, 420, 550), t, 1.40, W * 0.64, 520,
                     ry=-16, rz=6, exit_t=3.04)
            self.arc(ov, t, 2.20, W * 0.52, 520, 330)
        if 5.12 <= t < 6.6:
            for k, (st, kind, lab, pr) in enumerate(((5.52, "bag", "Bag", "$640"), (5.80, "watch", "Watch", "$720"),
                                                     (6.06, "shoe", "Sneakers", "$290"))):
                self.fly(ov, sf.item_card(kind, lab, pr), t, st, 230 + k * 310, 600 + (k % 2) * 40, ry=(k - 1) * -14,
                         rz=(k - 1) * 5, from_y=-600, exit_t=6.40)
        if 8.77 <= t < 10.2:
            self.fly(ov, sf.gloss_tile("card", 300), t, 9.0, W / 2, 560, ry=-20, rx=12, rz=-6, glow_c=LIME, exit_t=10.05)
            if t >= 9.25:
                q = spring(t - 9.25, 14, 0.6)
                badge = pv4.word_img("+ $3,600", "black", 60, INK)
                bp = Image.new("RGBA", (badge.width + 50, badge.height + 26), (0, 0, 0, 0))
                ImageDraw.Draw(bp).rounded_rectangle((0, 0, bp.width - 1, bp.height - 1), bp.height // 2, fill=LIME + (255,))
                bp.alpha_composite(badge, (25, 13))
                place(ov, sf.drop_shadow(bp, 16, 0.2, 12), W * 0.68, 790, scale=max(q, 0.01),
                      alpha=1 - smooth((t - 9.95) / 0.12), anchor="c")
        if 10.54 <= t < 13.8:
            cards = ((10.54, "car", "The car", "upgraded"), (11.08, "house", "The house", "upgraded"),
                     (11.62, "jetski", "The vacation", "upgraded"))
            for k, (st, key, title, sub) in enumerate(cards):
                self.fly(ov, sf.photo_card(key, title, sub, w), t, st, W / 2 + (k - 1) * 230, 610 + abs(k - 1) * 30,
                         ry=(k - 1) * -18, rz=(k - 1) * 7, glow_c=LIME, exit_t=13.40)
            self.arc(ov, t, 11.62, W / 2, 600, 420)

    def frame(self, fi):
        t = fi / FPS
        i = fi + 1
        z = self.zoom(t) * self.punch(t)
        base, m = self.footage(i, t, z)
        base = base * self.top_shade
        behind = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        front = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        for on, off, kick, big, extra, et in TYPE:
            if not (on - 0.12 <= t < off):
                continue
            bw = big_word(big)
            bx = (W - bw.width) / 2
            dx, bl, al = self.whip(t, on, off)
            sh = Image.new("RGBA", bw.size, (0, 0, 0, 0))
            sh.putalpha(bw.getchannel("A").filter(ImageFilter.GaussianBlur(18)).point(lambda v: int(v * 0.5)))
            place(behind, pv4.hblur(sh, bl), bx + dx, TOP + 16, alpha=al)
            place(behind, pv4.hblur(bw, bl), bx + dx, TOP, alpha=al)
            if kick:
                kp = expo((t - on + 0.12) / 0.35)
                ki = pv4.word_img(kick, "light", 96 if len(kick) < 9 else 74, WHITE)
                place(front, ki, bx + 14 + (1 - kp) * -50, TOP - ki.height * 0.60, alpha=kp * (al if t > on else 1))
            if extra and t >= et:
                q = spring(t - et, 14, 0.6)
                ei = pv4.word_img(extra, "blacki", 92, WHITE)
                if ei.width > W - 120:
                    ei = ei.resize((W - 120, int(ei.height * (W - 120) / ei.width)), Image.LANCZOS)
                ex = min(bx + bw.width - ei.width * 0.75, W - ei.width - 40)
                place(front, ei, ex + (1 - min(q, 1)) * 70, TOP + bw.height * 0.80, alpha=min(1, q * 1.6) * al,
                      scale=1.12 - 0.12 * min(q, 1))
        ba = np.asarray(behind).astype(np.float32) / 255
        al_ = ba[..., 3:4] * (1 - m[..., None])
        out = base * (1 - al_) + ba[..., :3] * al_
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        self.overlay(ov, t)
        ov.alpha_composite(front)
        # one-word captions at chest height
        cur = [x for x in self.words if x[0] - 0.02 <= t < max(x[1], x[0] + 0.18) + 0.06]
        if cur:
            st, en, wd = cur[-1]
            wd = wd.lower().strip(".,!?")
            q = expo((t - st + 0.02) / 0.16)
            ci = pv4.word_img(wd, "med", 70, WHITE)
            cs = Image.new("RGBA", ci.size, (0, 0, 0, 0))
            cs.putalpha(ci.getchannel("A").filter(ImageFilter.GaussianBlur(12)).point(lambda v: int(v * 0.7)))
            place(ov, cs, W / 2, CAP_Y + 6, alpha=q, anchor="c")
            place(ov, ci, W / 2, CAP_Y, alpha=q, scale=1.14 - 0.14 * q, anchor="c")
            if any(a <= t < b for a, b in BRACKETS):
                d = ImageDraw.Draw(ov)
                bw2, bh2, L = max(ci.width + 130, 400), 170, 40
                x0, y0, x1, y1 = W / 2 - bw2 / 2, CAP_Y - bh2 / 2, W / 2 + bw2 / 2, CAP_Y + bh2 / 2
                for cx, cy, sx, sy in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
                    d.line((cx, cy, cx + sx * L, cy), fill=WHITE + (235,), width=5)
                    d.line((cx, cy, cx, cy + sy * L), fill=WHITE + (235,), width=5)
        oa = np.asarray(ov).astype(np.float32) / 255
        out = out * (1 - oa[..., 3:4]) + oa[..., :3] * oa[..., 3:4]
        for b in sf.WHIP:
            d = t - b
            if -0.08 <= d < 0.12:
                k = 1 - abs(d) / (0.08 if d < 0 else 0.12)
                out = np.roll(cv2.blur(out, (int(1 + 120 * k) | 1, 1)), int(W * 0.3 * k * (-1 if d < 0 else 1)), axis=1)
        if any(0 <= t - f0 < 2 / FPS + 1e-6 for f0 in sf.FLASH):
            lum = out.mean(2)
            sil = np.clip((m > 0.5) * (lum < 0.5) + (oa[..., 3] > 0.5) + (ba[..., 3] > 0.5), 0, 1).astype(np.float32)
            sil = cv2.medianBlur((sil * 255).astype(np.uint8), 5).astype(np.float32) / 255
            out = np.dstack([sil] * 3) + (1 - sil[..., None]) * (np.array(INK) / 255)
        rng = np.random.default_rng(fi)
        out = out + rng.standard_normal(out.shape[:2]).astype(np.float32)[..., None] * 0.012
        return (np.clip(out, 0, 1) * 255).astype(np.uint8)


class Page:
    """Before / After page (AVE colours, Poppins), Braiden raw in B&W on the left."""

    def __init__(self, work, fonts_work):
        pv2.FD = os.path.join(fonts_work, "fonts")
        self.edit = Edit(work)
        self.page = pv2.build_page()
        bs, bp = pv2.shadow_layer(BEFORE, a=0.16)
        self.page.alpha_composite(bs, bp)
        self.card_shadow = pv2.shadow_layer(CARD)
        self.card_mask = pv2.rounded_mask(CARD[2], CARD[3], pv2.RADIUS)
        self.before_mask = pv2.rounded_mask(BEFORE[2], BEFORE[3], pv2.RADIUS)

    def before(self, i, t):
        k = next(n for n, (a, b) in enumerate(sf.SHOTS) if a <= t < b or n == len(sf.SHOTS) - 1)
        cx = self.edit.shot_geo[k][1]
        cw = 608 * BEFORE[2] / BEFORE[3]
        x0 = min(max(cx - cw / 2, 0), 1080 - cw)
        im = self.edit.raw(i).resize((BEFORE[2], BEFORE[3]), Image.LANCZOS, box=(x0, 0, x0 + cw, 608)).convert("L")
        im = im.convert("RGBA"); im.putalpha(self.before_mask)
        return im

    def frame(self, fi):
        t = fi / FPS
        i = fi + 1
        after = Image.fromarray(self.edit.frame(fi)).resize((CARD[2], CARD[3]), Image.LANCZOS).convert("RGBA")
        after.putalpha(self.card_mask)
        page = self.page.copy()
        page.alpha_composite(self.before(i, t), (BEFORE[0], BEFORE[1]))
        page.alpha_composite(self.card_shadow[0], self.card_shadow[1])
        page.alpha_composite(after, (CARD[0], CARD[1]))
        return np.asarray(page.convert("RGB"))


SFX = ([(t, "whoosh") for t in (1.30, 3.13, 5.52, 8.77, 9.0, 10.54, 11.08, 11.62, 13.4)]
       + [(t, "air") for t, *_ in TYPE]
       + [(t, "thock") for t in (4.90, 7.82, 10.24, 15.98)]
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
            Image.fromarray(P.frame(fi)).save(os.path.join(work, f"ba_{fi:04d}.png"))
        return
    vid = os.path.join(work, "video_ba.mp4")
    p = subprocess.Popen(f'ffmpeg -v error -y -f rawvideo -pix_fmt rgb24 -s {W}x{H} -r {FPS} -i - '
                         f'-c:v libx264 -preset slow -crf 15 -pix_fmt yuv420p "{vid}"', shell=True, stdin=subprocess.PIPE)
    with Pool(3, initializer=_init, initargs=(work, fonts_work)) as pool:
        for buf in pool.imap(_frame, range(N), chunksize=3):
            p.stdin.write(buf)
    p.stdin.close(); p.wait()
    mix, master = os.path.join(work, "mix_ba.wav"), os.path.join(work, "master_ba.wav")
    b1.build_audio(work, mix, music, start)
    v1.loudnorm(mix, master)
    out = os.path.join(work, "AVE_Braiden_Before_After.mp4")
    v1.sh(f'ffmpeg -v error -y -i "{vid}" -i "{master}" -c:v copy -c:a aac -b:a 256k -shortest -movflags +faststart "{out}"')
    print(out)


if __name__ == "__main__":
    cmd, work, fonts_work = sys.argv[1:4]
    if cmd == "render":
        render(work, fonts_work, sys.argv[4] if len(sys.argv) > 4 else None, float(sys.argv[5]) if len(sys.argv) > 5 else 0.0)
    elif cmd == "stills":
        render(work, fonts_work, only=[int(round(float(x) * FPS)) for x in sys.argv[4:]])
