"""AVE Studio · Before / After talking-head reel (1080x1920, 30 fps).

Rebuilds a creator's talking-head clip in AVE's look, using a third-party
"Before / After" portfolio reel only as a timing and layout reference.
Nothing graphic from the reference is reused: the only things taken from it
are the creator's raw footage (the black-and-white "Before" panel) and his
voice (separated from the reference's music and effects with Demucs).
The creator's permission for this use must be kept on record.

Usage:
    python build.py prep   REF.mp4 WORK_DIR   # crop + upscale, voice stem, transcript, cut-outs
    python build.py render REF.mp4 WORK_DIR   # frames + sound -> WORK_DIR/AVE_Before_After.mp4

Media stays in WORK_DIR and is never committed.
"""
import json, math, os, subprocess, sys
from functools import lru_cache

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FONTS = os.path.join(ROOT, "ave-promo", "film", "fonts")

W, H, FPS = 1080, 1920, 30

# ---- brand (brand/tokens.json) -------------------------------------------
INK = (14, 14, 14)
PAPER = (243, 242, 238)
LIME = (200, 255, 46)
RAISED = (233, 230, 223)       # surface-raised, Paper theme
RAISED_INK = (28, 27, 25)      # surface-raised, Ink theme
MUTED = (111, 107, 100)        # text-muted, Paper
GREY300 = (214, 212, 205)
GREY500 = (138, 135, 127)

# ---- reference geometry (720x1280 source) ---------------------------------
# The "Before" panel in the reference sits at x 78..282, y 358..867 (measured);
# its right edge is hidden under the reference's "After" card.
BEFORE_CROP = "199:466:81:362"        # inner panel, clear of rounded corners and UI
AFTER_CROP = "198:352:81:368"         # head-and-shoulders region for our After card

# ---- our layout (1080x1920) ----------------------------------------------
CARD = (425, 435, 540, 960)           # x, y, w, h of the After card
BEFORE = (110, 537, 330, 772)         # Before panel (partly under the card)
RADIUS = 24

# ---- timeline (seconds), from the transcript and the reference's cuts ------
END = 1355 / FPS
SEGMENTS = [  # (start, end, kind, arg)
    (0.00, 5.87, "spk", None), (5.87, 7.77, "num", 1), (7.77, 11.50, "spk", None),
    (11.50, 17.70, "insp", None), (17.70, 20.47, "spk", None), (20.47, 22.00, "num", 2),
    (22.00, 30.47, "spk", None), (30.47, 33.00, "num", 3), (33.00, 36.90, "spk", None),
    (36.90, 41.20, "fx", None), (41.20, END, "spk", None),
]
NUM_CARDS = {  # number, number-in time, (small word, t), (title, t), icon
    1: (6.10, ("lack of", 6.62), ("DIRECTION", 7.00), "compass"),
    2: (20.58, ("bad", 21.12), ("DESIGN", 21.36), "grid"),
    3: (31.14, ("poor", 31.72), ("POST-\nPRODUCTION", 31.94), "spark"),
}
BIG = [  # big condensed word behind the speaker: (on, off, text, icon)
    (0.62, 2.76, "EDITS", None), (3.50, 5.87, "INSTAGRAM", "phone"),
    (9.26, 11.50, "EXACTLY", "bulb"), (18.30, 20.47, "LOST", "pin"),
    (22.14, 24.87, "DESIGN", "grid"), (29.52, 30.47, "BEGINNER", None),
    (33.08, 35.42, "PRODUCTION", "spark"), (36.30, 36.90, "EFFECTS", None),
    (41.94, END, "REMEMBER", None),
]
FLASH = [0.62, 3.50, 9.26, 18.30, 29.52, 33.08, 36.30, 41.94]   # lens flash on punch words
KICK = [  # small kicker line above the big word
    (0.00, 2.76, "IF YOU LOOK AT YOUR"), (2.76, 5.87, "LIKE WHAT I SEE ON"),
    (8.62, 11.50, "YOU NEED TO KNOW"), (17.74, 20.47, "THEN YOU'RE GONNA GET"),
    (29.00, 30.47, "YOU'RE A"), (33.00, 35.42, "POST"),
    (35.42, 36.90, "YOU NEED TO LOOK INTO"), (41.20, END, "JUST MAKE SURE TO"),
]
CAPS = [  # (small on, big on, off, small line, big line, small below big?)
    (0.84, 1.76, 2.76, "and you think", "THAT LOOKS NOTHING", False),
    (4.10, 4.74, 5.36, "it's probably", "ONE OF THESE", False),
    (7.77, 7.94, 8.62, "to create", "A GOOD EDIT", False),
    (9.74, 10.36, 11.50, "what you want", "YOUR SCENE TO LOOK LIKE", False),
    (18.84, 19.18, 20.47, "and your edit", "IS NOT GONNA LOOK THAT GOOD", False),
    (24.02, 22.42, 24.87, "for video editors.", "IS THE MOST IMPORTANT SKILL", True),
    (28.32, None, 29.00, "all signal that", None, False),
    (33.64, 33.84, 35.42, "is what", "BRINGS YOUR ANIMATIONS TO LIFE", False),
    (42.96, 44.02, END, "the next time your edit", "LOOKS BORING.", False),
]
CHECKS = [(25.26, "Imbalanced scenes"), (26.46, "Bad contrast"), (27.26, "Uncommon patterns")]
CHECKS_OFF = 30.47
BUBBLES = [(5.36, 5.87, ["?", "?", "?"]), (42.50, END, ["1", "2", "3"])]
FX_ROWS = [(37.06, "Vignette", "vignette"), (37.76, "Blur", "blur"),
           (38.46, "Chromatic aberration", "chroma"), (39.62, "Noise", "noise"),
           (40.30, "Posterize time", "poster")]
INSP = dict(vault=12.20, vault_word=12.56, house=13.70, fan=14.22, refs=14.80, count_end=17.20)

# One sound per real visual change.
SFX = ([(t, "whoosh") for t in (5.87, 7.77, 11.50, 17.70, 20.47, 22.00, 30.47, 33.00, 36.90, 41.20)]
       + [(t, "thock") for t in (6.10, 20.58, 31.14, 13.70)]
       + [(t, "flash") for t in (0.62, 3.50, 9.26, 18.30, 29.52, 36.30, 41.94)]
       + [(t, "bloop") for t in (5.36, 25.26, 26.46, 27.26, 42.50, 12.20)]
       + [(14.22, "air")]
       + [(t + 0.15, "ding") for t, _, _ in FX_ROWS])


# ===========================================================================
# prep
# ===========================================================================
def sh(cmd):
    subprocess.run(cmd, shell=True, check=True)


def prep(ref, work):
    os.makedirs(work, exist_ok=True)
    au, bu, mk = (os.path.join(work, d) for d in ("after_up", "before_up", "mask"))
    for d in (au, bu, mk):
        os.makedirs(d, exist_ok=True)
    # 1. crop the raw B&W panel and upscale carefully (denoise, lanczos, light unsharp)
    if not os.listdir(au):
        sh(f'ffmpeg -v error -i "{ref}" -vf "crop={AFTER_CROP},hqdn3d=1.5:1.5:4:4,'
           f'scale={CARD[2]}:{CARD[3]}:flags=lanczos,unsharp=5:5:0.7:5:5:0,format=gray" "{au}/%04d.png"')
    if not os.listdir(bu):
        sh(f'ffmpeg -v error -i "{ref}" -vf "crop={BEFORE_CROP},hqdn3d=1.5:1.5:4:4,'
           f'scale={BEFORE[2]}:{BEFORE[3]}:flags=lanczos,unsharp=5:5:0.5:5:5:0,format=gray" "{bu}/%04d.png"')
    # 2. voice: separate speech from the reference's music bed and effects
    voc = os.path.join(work, "voice.wav")
    if not os.path.exists(voc):
        import soundfile as sf, torch
        from demucs.pretrained import get_model
        from demucs.apply import apply_model
        tmp = os.path.join(work, "ref44.wav")
        sh(f'ffmpeg -v error -y -i "{ref}" -vn -ar 44100 -ac 2 "{tmp}"')
        m = get_model("htdemucs_ft"); m.eval()
        a, sr = sf.read(tmp, dtype="float32")
        x = torch.tensor(a.T)[None]
        r = x.mean(1, keepdim=True)
        with torch.no_grad():
            out = apply_model(m, (x - r.mean()) / r.std(), shifts=1, split=True, overlap=0.25)[0]
        out = out * r.std() + r.mean()
        sf.write(voc, out[m.sources.index("vocals")].numpy().T, sr)
    # 3. transcript with word timings (used to place every cue above)
    wj = os.path.join(work, "words.json")
    if not os.path.exists(wj):
        from faster_whisper import WhisperModel
        raw = subprocess.run(f'ffmpeg -v error -i "{voc}" -ac 1 -ar 16000 -f f32le -',
                             shell=True, check=True, capture_output=True).stdout
        segs, _ = WhisperModel("small.en", compute_type="int8").transcribe(
            np.frombuffer(raw, np.float32), word_timestamps=True)
        json.dump([[w.start, w.end, w.word.strip()] for s in segs for w in s.words], open(wj, "w"))
    # 4. per-frame cut-out of the speaker
    from rembg import remove, new_session
    sess = new_session("u2net_human_seg")
    for f in sorted(os.listdir(au)):
        o = os.path.join(mk, f)
        if not os.path.exists(o):
            remove(Image.open(os.path.join(au, f)).convert("RGB"), session=sess, only_mask=True).save(o)


# ===========================================================================
# drawing helpers
# ===========================================================================
@lru_cache(None)
def font(name, size):
    files = {"xb": "InterDisplay-ExtraBold.otf", "b": "InterDisplay-Bold.otf",
             "sb": "InterDisplay-SemiBold.otf", "md": "InterDisplay-Medium.otf",
             "serif": "InstrumentSerif-italic-400.woff2", "mono": "JetBrainsMono-normal-500.woff2"}
    return ImageFont.truetype(os.path.join(FONTS, files[name]), size)


@lru_cache(None)
def text_img(txt, name, size, color, track=0.0, condense=1.0, stroke=0, stroke_color=INK):
    """Render text to a tight RGBA image. track is em letter-spacing; condense squeezes x."""
    f = font(name, size)
    lines = txt.split("\n")
    lh = int(size * 0.92) if name == "xb" else int(size * 1.15)
    ws = []
    for ln in lines:
        w = sum(f.getlength(c) for c in ln) + track * size * max(len(ln) - 1, 0) if track else f.getlength(ln)
        ws.append(w)
    iw, ih = int(max(ws) + size + 2 * stroke), int(lh * (len(lines) - 1) + size * 1.4 + 2 * stroke)
    im = Image.new("RGBA", (iw, ih), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i, ln in enumerate(lines):
        y = stroke + i * lh
        if track:
            x = stroke
            for c in ln:
                d.text((x, y), c, font=f, fill=color + (255,))
                x += f.getlength(c) + track * size
        else:
            d.text((stroke, y), ln, font=f, fill=color + (255,), stroke_width=stroke, stroke_fill=stroke_color + (255,))
    im = im.crop(im.getbbox())
    if condense != 1.0:
        im = im.resize((max(1, int(im.width * condense)), im.height), Image.LANCZOS)
    return im


def fit(im, maxw, maxh):
    k = min(maxw / im.width, maxh / im.height, 1e9)
    return im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.LANCZOS)


def ease_out(p):
    p = min(max(p, 0.0), 1.0)
    return 1 - (1 - p) ** 3


def back_out(p, s=1.9):
    p = min(max(p, 0.0), 1.0) - 1
    return 1 + (s + 1) * p ** 3 + s * p ** 2


def paste(base, im, x, y, alpha=1.0, scale=1.0, anchor="lt"):
    if alpha <= 0.003 or scale <= 0.01:
        return
    if scale != 1.0:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.LANCZOS)
    if alpha < 1.0:
        im = im.copy()
        im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    if anchor == "c":
        x, y = x - im.width / 2, y - im.height / 2
    elif anchor == "ct":
        x = x - im.width / 2
    base.alpha_composite(im, (int(round(x)), int(round(y))))


def rounded_mask(w, h, r, ss=4):
    m = Image.new("L", (w * ss, h * ss), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w * ss - 1, h * ss - 1), r * ss, fill=255)
    return m.resize((w, h), Image.LANCZOS)


# ---- line icons (drawn 4x, downsampled) -----------------------------------
@lru_cache(None)
def icon(kind, size, color, bg=None, lw=None):
    ss = 4
    S = size * ss
    lw = (lw or max(2, size // 14)) * ss
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = color + (255,)
    if bg:
        d.rounded_rectangle((0, 0, S - 1, S - 1), S // 4, fill=bg + (255,))
    p = S * 0.22 if bg else S * 0.08
    a, b = p, S - p  # inner box
    m = S / 2
    if kind == "bulb":
        d.ellipse((m - S * .26, a, m + S * .26, a + S * .52), outline=c, width=lw)
        d.line((m - S * .12, b - S * .2, m + S * .12, b - S * .2), fill=c, width=lw)
        d.line((m - S * .09, b - S * .07, m + S * .09, b - S * .07), fill=c, width=lw)
        d.line((m, a + S * .2, m, a + S * .42), fill=c, width=lw)
    elif kind == "pin":
        d.ellipse((m - S * .24, a, m + S * .24, a + S * .48), outline=c, width=lw)
        d.ellipse((m - S * .08, a + S * .16, m + S * .08, a + S * .32), fill=c)
        d.line((m - S * .17, a + S * .4, m, b), fill=c, width=lw)
        d.line((m + S * .17, a + S * .4, m, b), fill=c, width=lw)
    elif kind == "phone":
        d.rounded_rectangle((m - S * .2, a, m + S * .2, b), S * .07, outline=c, width=lw)
        d.line((m - S * .06, a + S * .08, m + S * .06, a + S * .08), fill=c, width=lw)
        d.polygon([(m - S * .06, m - S * .1), (m - S * .06, m + S * .1), (m + S * .1, m)], fill=c)
    elif kind == "grid":
        q = (b - a) / 2
        for i in range(2):
            for j in range(2):
                box = (a + i * q + lw, a + j * q + lw, a + (i + 1) * q - lw, a + (j + 1) * q - lw)
                (d.rounded_rectangle(box, S * .04, fill=c) if (i + j) % 2 == 0 else
                 d.rounded_rectangle(box, S * .04, outline=c, width=lw))
    elif kind == "spark":
        r1, r2 = (b - a) / 2, (b - a) * 0.1
        pts = []
        for k in range(8):
            r = r1 if k % 2 == 0 else r2
            t = k * math.pi / 4 - math.pi / 2
            pts.append((m + r * math.cos(t), m + r * math.sin(t)))
        d.polygon(pts, fill=c)
    elif kind == "compass":
        d.ellipse((a, a, b, b), outline=c, width=lw)
        d.polygon([(m, a + S * .1), (m + S * .09, m), (m, b - S * .1), (m - S * .09, m)], fill=c)
    elif kind == "vignette":
        d.rounded_rectangle((a, a, b, b), S * .08, outline=c, width=lw)
        d.ellipse((a + S * .12, a + S * .12, b - S * .12, b - S * .12), outline=c, width=lw)
    elif kind == "blur":
        d.polygon([(m, a), (m + S * .24, m + S * .05), (m - S * .24, m + S * .05)], fill=c)
        d.ellipse((m - S * .24, m - S * .15, m + S * .24, b), fill=c)
    elif kind == "chroma":
        r = S * .17
        for dx, dy in ((-.1, -.06), (.1, -.06), (0, .1)):
            d.ellipse((m + dx * S - r, m + dy * S - r, m + dx * S + r, m + dy * S + r), outline=c, width=lw)
    elif kind == "noise":
        for i in range(4):
            for j in range(4):
                if (i * 3 + j * 5) % 3:
                    x, y = a + (i + .5) * (b - a) / 4, a + (j + .5) * (b - a) / 4
                    d.ellipse((x - S * .04, y - S * .04, x + S * .04, y + S * .04), fill=c)
    elif kind == "poster":
        st = (b - a) / 4
        pts = [(a, b)]
        for k in range(4):
            pts += [(a + k * st, b - (k + 1) * st), (a + (k + 1) * st, b - (k + 1) * st)]
        d.line(pts, fill=c, width=lw, joint="curve")
    elif kind == "check":
        d.line([(a + S * .05, m), (m - S * .06, b - S * .12), (b - S * .02, a + S * .12)], fill=c, width=lw, joint="curve")
    elif kind == "vault":
        d.rounded_rectangle((a, a, b, b), S * .08, outline=c, width=lw)
        d.ellipse((m - S * .22, m - S * .22, m + S * .22, m + S * .22), outline=c, width=lw)
        for k in range(4):
            t = k * math.pi / 2 + math.pi / 4
            d.line((m, m, m + S * .22 * math.cos(t), m + S * .22 * math.sin(t)), fill=c, width=lw)
        d.line((b - S * .1, m - S * .12, b - S * .1, m + S * .12), fill=c, width=lw)
    return im.resize((size, size), Image.LANCZOS)


# ===========================================================================
# static layers
# ===========================================================================
def build_page():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    page = np.ones((H, W, 3), np.float32) * np.array(PAPER, np.float32)
    lime = np.array(LIME, np.float32)
    for cx, cy, r, a in ((1020, 80, 380, 0.15), (30, 1860, 420, 0.12)):   # soft lime glow
        g = np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * r * r)))[..., None] * a
        page = page * (1 - g) + lime * g
    img = Image.fromarray(page.clip(0, 255).astype(np.uint8)).convert("RGBA")

    # top line
    t = text_img("EDITED BY AVE STUDIO", "mono", 28, INK, track=0.12)
    dot = 14
    tw = t.width + dot + 16
    x0 = (W - tw) / 2
    ImageDraw.Draw(img).ellipse((x0, 290 + t.height / 2 - dot / 2, x0 + dot, 290 + t.height / 2 + dot / 2), fill=LIME + (255,))
    ImageDraw.Draw(img).ellipse((x0, 290 + t.height / 2 - dot / 2, x0 + dot, 290 + t.height / 2 + dot / 2), outline=INK + (255,), width=2)
    paste(img, t, x0 + dot + 16, 290)

    # chips
    def chip(x, y, label, fill, fg, dotc):
        lab = text_img(label, "mono", 26, fg, track=0.12)
        w, h = lab.width + 86, 52
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((x, y, x + w, y + h), h // 2, fill=fill + (255,))
        d.ellipse((x + 20, y + h / 2 - 8, x + 36, y + h / 2 + 8), fill=dotc + (255,))
        paste(img, lab, x + 52, y + (h - lab.height) / 2)
    chip(BEFORE[0], BEFORE[1] - 70, "BEFORE", RAISED, INK, GREY500)
    chip(CARD[0], CARD[1] - 70, "AFTER", INK, PAPER, LIME)

    # call to action
    a = text_img("Comment", "md", 70, INK)
    b = text_img("“SAMPLE”", "xb", 70, INK)
    gap = 22
    total = a.width + gap + b.width
    x = (W - total) / 2
    y = 1500
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((x + a.width + gap - 14, y - 10, x + total + 14, y + b.height + 14), 12, fill=LIME + (255,))
    paste(img, a, x, y + b.height - a.height)
    paste(img, b, x + a.width + gap, y)
    s1 = text_img("and I'll send you the project", "md", 40, MUTED)
    s2 = text_img("file.", "serif", 48, INK)
    tot = s1.width + 12 + s2.width
    paste(img, s1, (W - tot) / 2, 1610)
    paste(img, s2, (W - tot) / 2 + s1.width + 12, 1610 + s1.height - s2.height + 6)
    return img


def shadow_layer(box, r=RADIUS, oy=14, blur=32, a=0.18, pad=90):
    x, y, w, h = box
    sh_ = Image.new("L", (w + 2 * pad, h + 2 * pad), 0)
    sh_.paste(rounded_mask(w, h, r), (pad, pad + oy))
    sh_ = sh_.filter(ImageFilter.GaussianBlur(blur / 2))
    lay = Image.new("RGBA", sh_.size, INK + (0,))
    lay.putalpha(sh_.point(lambda v: int(v * a)))
    return lay, (x - pad, y - pad)


def paper_card_bg():
    w, h = CARD[2], CARD[3]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dist = np.sqrt(((xx - w / 2) / (w * 0.62)) ** 2 + ((yy - h / 2) / (h * 0.62)) ** 2)
    v = np.clip((dist - 0.45) / 0.6, 0, 1)[..., None] ** 1.5
    bg = np.array(PAPER, np.float32) * (1 - v) + np.array(RAISED, np.float32) * v * 0.97
    g = np.exp(-dist ** 2 / 0.08)[..., None] * 0.10
    bg = bg * (1 - g) + np.array(LIME, np.float32) * g
    return Image.fromarray(bg.astype(np.uint8)).convert("RGBA")


def flash_field():
    w, h = CARD[2], CARD[3]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy = w * 0.78, 175
    core = np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * 55 ** 2)))
    streak = np.exp(-(((xx - cx) / 260) ** 2 + ((yy - cy) / 5) ** 2))
    halo = np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * 220 ** 2)))
    f = core[..., None] * np.array([1, 1, 0.92]) + streak[..., None] * np.array([0.85, 1, 0.45]) * 0.9 \
        + halo[..., None] * np.array([0.78, 1, 0.18]) * 0.35
    return (f * 255).astype(np.float32)


# ===========================================================================
# card content
# ===========================================================================
def active(lst, t, i_on=0, i_off=1):
    return [e for e in lst if e[i_on] <= t < e[i_off]]


def seg_at(t):
    for s in SEGMENTS:
        if s[0] <= t < s[1]:
            return s
    return SEGMENTS[-1]


class Renderer:
    def __init__(self, work):
        self.work = work
        self.page = build_page()
        self.card_mask = rounded_mask(CARD[2], CARD[3], RADIUS)
        self.before_mask = rounded_mask(BEFORE[2], BEFORE[3], RADIUS)
        self.card_shadow = shadow_layer(CARD, a=0.28, blur=40)
        bs, bp = shadow_layer(BEFORE)
        self.page.alpha_composite(bs, bp)
        self.paper_bg = paper_card_bg()
        self.flash = flash_field()
        yy = np.arange(CARD[3], dtype=np.float32)
        self.shade = (1 - 0.55 * np.clip((yy - 640) / 320, 0, 1) ** 1.3)[:, None, None]
        self.n = len(os.listdir(os.path.join(work, "after_up")))

    # ---- footage ---------------------------------------------------------
    def frame_gray(self, d, i):
        i = min(max(i, 1), self.n)
        return cv2.imread(os.path.join(self.work, d, f"{i:04d}.png"), cv2.IMREAD_GRAYSCALE)

    def speaker(self, i, t, seg):
        g = self.frame_gray("after_up", i).astype(np.float32) / 255
        m = self.frame_gray("mask", i).astype(np.float32) / 255
        # slow push-in across the segment, anchored on the face
        p = (t - seg[0]) / max(seg[1] - seg[0], 0.1)
        k = 1.0 + 0.045 * ease_out(p)
        if k > 1.0001:
            M = cv2.getRotationMatrix2D((CARD[2] * 0.62, 450), 0, k)
            g = cv2.warpAffine(g, M, (CARD[2], CARD[3]), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            m = cv2.warpAffine(m, M, (CARD[2], CARD[3]), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        m = cv2.GaussianBlur(np.clip((m - 0.15) / 0.7, 0, 1), (0, 0), 1.2)
        # grade: neutral / slightly cool on the person, near-black room
        pg = np.clip((g - 0.035) / 0.93, 0, 1) ** 1.06
        person = np.stack([pg * 0.965, pg * 0.985, pg * 1.03], -1)
        room = np.stack([g, g, g], -1) * 0.10 + np.array(INK) / 255 * 0.9
        # lime rim light from camera-left and above
        sl = np.zeros_like(m); sl[:, 7:] = m[:, :-7]
        st = np.zeros_like(m); st[6:, :] = m[:-6, :]
        edge = np.clip(m - sl, 0, 1) + 0.55 * np.clip(m - st, 0, 1)
        rim = cv2.GaussianBlur(np.clip(edge, 0, 1), (0, 0), 2.5) * m
        glow = cv2.GaussianBlur(np.clip(m - sl, 0, 1), (0, 0), 18) * (1 - m) * 0.5
        lime = np.array(LIME, np.float32) / 255
        return person, room, m, rim, glow, lime

    def compose_speaker(self, i, t, seg):
        person, room, m, rim, glow, lime = self.speaker(i, t, seg)
        w, h = CARD[2], CARD[3]
        # background + big word behind the speaker
        bgimg = Image.fromarray((np.clip(room + glow[..., None] * lime, 0, 1) * 255).astype(np.uint8)).convert("RGBA")
        for on, off, txt, ic in active(BIG, t):
            p = ease_out((t - on) / 0.22)
            im = fit(text_img(txt, "xb", 260, PAPER, condense=0.6), w - 40, 300)
            paste(bgimg, im, w / 2, 160 + (1 - p) * 18, alpha=min(1, p * 1.4), scale=1.12 - 0.12 * p, anchor="ct")
        bg = np.asarray(bgimg.convert("RGB")).astype(np.float32) / 255
        rim_a = np.clip(rim * 0.85, 0, 0.7)[..., None]
        fg = person * (1 - rim_a) + lime * rim_a
        out = bg * (1 - m[..., None]) + fg * m[..., None]
        # lens flash on punch words
        fl = 0.0
        for t0 in FLASH:
            dt = t - t0
            if 0 <= dt < 0.45:
                fl = max(fl, (1 - dt / 0.45) ** 2)
        out = out * 255
        if fl > 0:
            out = out + self.flash * fl + 28 * fl
        out = out * self.shade
        img = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).convert("RGBA")

        # front graphics
        for on, off, txt, ic in active(BIG, t):
            if ic:
                p = back_out((t - on - 0.08) / 0.3)
                paste(img, icon(ic, 60, INK, bg=LIME), w - 56, 112, scale=max(p, 0.01), anchor="c")
        for on, off, txt in active(KICK, t):
            p = ease_out((t - on) / 0.2)
            paste(img, text_img(txt, "mono", 24, PAPER, track=0.12), w / 2, 62 + (1 - p) * 8, alpha=p, anchor="ct")
        for s_on, b_on, off, small, big, below in CAPS:
            if not (min(s_on, b_on or s_on) <= t < off):
                continue
            by = 790
            if big and t >= b_on:
                p = ease_out((t - b_on) / 0.2)
                bi = fit(text_img(big, "xb", 120, PAPER, condense=0.72), w - 70, 74)
                paste(img, bi, w / 2, by + (1 - p) * 14, alpha=p, anchor="ct")
            if small and t >= s_on:
                p = ease_out((t - s_on) / 0.2)
                si = text_img(small, "md", 32, PAPER)
                paste(img, si, w / 2, (by + 92 if below else by - 50) + (1 - p) * 8, alpha=p, anchor="ct")
        # checklist
        if CHECKS[0][0] <= t < CHECKS_OFF:
            for k, (on, label) in enumerate(CHECKS):
                if t < on:
                    continue
                p = ease_out((t - on) / 0.25)
                y = 600 + k * 70
                row = self.check_row(label)
                paste(img, row, 28 - (1 - p) * 40, y, alpha=p)
        # bubbles
        for on, off, marks in BUBBLES:
            if on <= t < off:
                for k, mk in enumerate(marks):
                    p = back_out((t - on - k * 0.08) / 0.32)
                    if p > 0.01:
                        paste(img, self.bubble(mk), w / 2 + (k - 1) * 110, 682, scale=p, anchor="c")
        return img

    @lru_cache(None)
    def check_row(self, label):
        lab = text_img(label, "sb", 30, PAPER)
        w, h = lab.width + 96, 56
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((0, 0, w - 1, h - 1), h // 2, fill=RAISED_INK + (235,))
        d.ellipse((12, 12, 44, 44), fill=LIME + (255,))
        im.alpha_composite(icon("check", 24, INK, lw=3), (16, 16))
        im.alpha_composite(lab, (60, (h - lab.height) // 2))
        return im

    @lru_cache(None)
    def bubble(self, mark):
        r = 46
        ss = 4
        im = Image.new("RGBA", (2 * r * ss, 2 * r * ss), (0, 0, 0, 0))
        ImageDraw.Draw(im).ellipse((0, 0, 2 * r * ss - 1, 2 * r * ss - 1), fill=LIME + (255,), outline=INK + (255,), width=3 * ss)
        im = im.resize((2 * r, 2 * r), Image.LANCZOS)
        tx = text_img(mark, "xb", 52, INK)
        im.alpha_composite(tx, ((2 * r - tx.width) // 2, (2 * r - tx.height) // 2))
        return im

    # ---- paper cards -----------------------------------------------------
    def compose_number(self, t, n):
        img = self.paper_bg.copy()
        t_num, (small, t_s), (title, t_t), ic = NUM_CARDS[n]
        num = text_img(str(n), "xb", 360, LIME, stroke=5, stroke_color=INK)
        x0, ybase = 56, 640
        if t >= t_num:
            p = ease_out((t - t_num) / 0.4)
            # soft drop shadow
            shd = Image.new("RGBA", num.size, INK + (0,))
            shd.putalpha(num.getchannel("A").point(lambda v: int(v * 0.16)))
            shd = shd.filter(ImageFilter.GaussianBlur(10))
            # build in: reveal from the baseline upward
            vis = max(1, int(num.height * p))
            part = num.crop((0, num.height - vis, num.width, num.height))
            spart = shd.crop((0, num.height - vis, num.width, num.height))
            paste(img, spart, x0 + 16, ybase - vis + 20)
            paste(img, part, x0, ybase - vis)
        tx = x0 + num.width + 26
        ti = fit(text_img(title, "xb", 200, INK, condense=0.62), CARD[2] - tx - 34, num.height - 120)
        si = text_img(small, "md", 44, MUTED)
        ty = ybase - ti.height
        if t >= t_s:
            p = ease_out((t - t_s) / 0.25)
            paste(img, si, tx, ty - si.height - 18 + (1 - p) * 12, alpha=p)
            pi = back_out((t - t_s - 0.05) / 0.3)
            paste(img, icon(ic, 52, INK, bg=LIME), tx + si.width + 40, ty - si.height / 2 - 14,
                  scale=max(pi, 0.01), anchor="c")
        if t >= t_t:
            p = ease_out((t - t_t) / 0.28)
            paste(img, ti, tx, ty + (1 - p) * 30, alpha=p)
        return img

    def compose_insp(self, t):
        img = self.paper_bg.copy()
        w = CARD[2]
        T = INSP
        if t >= T["vault"]:
            p = back_out((t - T["vault"]) / 0.4)
            grow = 1.0 + 0.22 * ease_out((t - T["house"]) / 0.35) if t >= T["house"] else 1.0
            paste(img, icon("vault", 170, INK, lw=8), w / 2, 210, scale=max(p * grow, 0.01), anchor="c")
            # lime handle accent
            ImageDraw.Draw(img)
            vw = text_img("vault", "serif", 84, INK)
            hi = fit(text_img("INSPIRATION", "xb", 160, INK, condense=0.62), w - 80 - vw.width - 16, 100)
            hx = (w - hi.width - 16 - vw.width) / 2
            pa = ease_out((t - T["vault"]) / 0.3)
            paste(img, hi, hx, 350 + (1 - pa) * 20, alpha=pa)
            if t >= T["vault_word"]:
                pv = ease_out((t - T["vault_word"]) / 0.3)
                paste(img, vw, hx + hi.width + 16, 350 + hi.height - vw.height + 14 + (1 - pv) * 12, alpha=pv)
        if t >= T["fan"]:
            for k in range(5):
                p = ease_out((t - T["fan"] - k * 0.12) / 0.35)
                if p <= 0:
                    continue
                ang = (k - 2) * 9 * p
                th = self.thumb(k).rotate(ang, resample=Image.BICUBIC, expand=True)
                paste(img, th, w / 2 + (k - 2) * 78 * p, 600 + abs(k - 2) * 10 + (1 - p) * 60, alpha=p, anchor="c")
            n = 1 + int(999 * ease_out((t - T["fan"]) / (T["count_end"] - T["fan"])))
            paste(img, text_img(f"REF {n:04d}", "mono", 24, MUTED, track=0.12), 40, 40)
        if t >= T["refs"]:
            p = ease_out((t - T["refs"]) / 0.3)
            s = text_img("thousands of", "md", 36, MUTED)
            r = fit(text_img("REFERENCES", "xb", 160, INK, condense=0.62), w - 80, 100)
            paste(img, s, w / 2, 745 + (1 - p) * 10, alpha=p, anchor="ct")
            paste(img, r, w / 2, 792 + (1 - p) * 16, alpha=p, anchor="ct")
        return img

    @lru_cache(None)
    def thumb(self, k):
        ss = 3
        tw, th = 120, 160
        im = Image.new("RGBA", (tw * ss, th * ss), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((0, 0, tw * ss - 1, th * ss - 1), 14 * ss, fill=PAPER + (255,), outline=INK + (255,), width=3 * ss)
        if k == 2:
            d.rounded_rectangle((14 * ss, 14 * ss, (tw - 14) * ss, 90 * ss), 8 * ss, fill=LIME + (255,))
        else:
            d.rounded_rectangle((14 * ss, 14 * ss, (tw - 14) * ss, 90 * ss), 8 * ss, fill=GREY300 + (255,))
        d.line((14 * ss, 110 * ss, (tw - 14) * ss, 110 * ss), fill=INK + (255,), width=4 * ss)
        d.line((14 * ss, 128 * ss, (tw - 44) * ss, 128 * ss), fill=GREY500 + (255,), width=4 * ss)
        return im.resize((tw, th), Image.LANCZOS)

    def compose_fx(self, t):
        img = self.paper_bg.copy()
        w = CARD[2]
        hd = text_img("EFFECT CONTROLS", "mono", 24, MUTED, track=0.12)
        p0 = ease_out((t - 36.9) / 0.25)
        paste(img, hd, 40, 110, alpha=p0)
        ImageDraw.Draw(img).line((40, 150, 40 + (w - 80) * p0, 150), fill=GREY300 + (255,), width=2)
        for k, (on, label, ic) in enumerate(FX_ROWS):
            if t < on:
                continue
            p = ease_out((t - on) / 0.28)
            on_p = ease_out((t - on - 0.15) / 0.15)
            paste(img, self.fx_row(label, ic, on_p > 0.5, round(on_p * 4) / 4), 40 + (1 - p) * 60, 190 + k * 118, alpha=p)
        return img

    @lru_cache(None)
    def fx_row(self, label, ic, on, knob):
        rw, rh = CARD[2] - 80, 92
        im = Image.new("RGBA", (rw, rh), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((0, 0, rw - 1, rh - 1), 18, fill=RAISED + (255,))
        im.alpha_composite(icon(ic, 44, INK, lw=3), (22, (rh - 44) // 2))
        lab = text_img(label, "sb", 27, INK)
        im.alpha_composite(lab, (84, (rh - lab.height) // 2))
        tw, th = 76, 40
        tx, ty = rw - tw - 22, (rh - th) // 2
        ss = 4
        tg = Image.new("RGBA", (tw * ss, th * ss), (0, 0, 0, 0))
        dg = ImageDraw.Draw(tg)
        dg.rounded_rectangle((0, 0, tw * ss - 1, th * ss - 1), th * ss // 2, fill=(LIME if on else GREY300) + (255,))
        kx = 4 + knob * (tw - th)
        dg.ellipse((kx * ss, 4 * ss, (kx + th - 8) * ss, (th - 4) * ss), fill=(INK if on else PAPER) + (255,))
        im.alpha_composite(tg.resize((tw, th), Image.LANCZOS), (tx, ty))
        return im

    # ---- frame -----------------------------------------------------------
    def frame(self, fi):
        t = fi / FPS
        i = fi + 1
        seg = seg_at(t)
        kind = seg[2]
        if kind == "spk":
            content = self.compose_speaker(i, t, seg)
        elif kind == "num":
            content = self.compose_number(t, seg[3])
        elif kind == "insp":
            content = self.compose_insp(t)
        else:
            content = self.compose_fx(t)
        # scale kick on every card change
        dt = t - seg[0]
        if seg[0] > 0 and dt < 0.2:
            k = 1.0 + 0.05 * (1 - ease_out(dt / 0.2))
            cw, ch = int(CARD[2] * k), int(CARD[3] * k)
            content = content.resize((cw, ch), Image.BILINEAR).crop(
                ((cw - CARD[2]) // 2, (ch - CARD[3]) // 2, (cw - CARD[2]) // 2 + CARD[2], (ch - CARD[3]) // 2 + CARD[3]))
        content.putalpha(self.card_mask)

        page = self.page.copy()
        b = Image.fromarray(self.frame_gray("before_up", i)).convert("RGBA")
        b.putalpha(self.before_mask)
        page.alpha_composite(b, (BEFORE[0], BEFORE[1]))
        page.alpha_composite(self.card_shadow[0], self.card_shadow[1])
        page.alpha_composite(content, (CARD[0], CARD[1]))
        return np.asarray(page.convert("RGB"))


# ===========================================================================
# sound: soft, creamy, synthesised in place (no third-party samples)
# ===========================================================================
SR = 48000


def env(n, a, d):
    t = np.arange(n) / SR
    return np.minimum(t / a, 1) * np.exp(-np.maximum(t - a, 0) / d)


def lowpass(x, fc):
    from scipy.signal import butter, sosfilt
    return sosfilt(butter(2, fc, "low", fs=SR, output="sos"), x)


def bandpass(x, lo, hi):
    from scipy.signal import butter, sosfilt
    return sosfilt(butter(2, [lo, hi], "band", fs=SR, output="sos"), x)


def make_sfx(kind, rng):
    if kind == "bloop":
        n = int(0.22 * SR); t = np.arange(n) / SR
        f = 260 + 300 * np.exp(-t / 0.035)
        x = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.004, 0.06)
        return lowpass(x + 0.2 * np.sin(4 * np.pi * np.cumsum(f) / SR) * env(n, 0.004, 0.04), 2500) * 0.9, 0.0
    if kind == "thock":
        n = int(0.3 * SR); t = np.arange(n) / SR
        f = 85 + 90 * np.exp(-t / 0.03)
        body = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.003, 0.09)
        click = lowpass(rng.standard_normal(n), 1400) * env(n, 0.001, 0.012) * 0.5
        return (body + click) * 0.95, 0.0
    if kind == "ding":
        n = int(0.6 * SR); t = np.arange(n) / SR
        x = (np.sin(2 * np.pi * 988 * t) + 0.3 * np.sin(2 * np.pi * 1976 * t) * np.exp(-t / 0.08)) * env(n, 0.003, 0.18)
        return lowpass(x, 4000) * 0.45, 0.0
    if kind in ("whoosh", "air"):
        dur = 0.5 if kind == "whoosh" else 0.7
        n = int(dur * SR); t = np.arange(n) / SR
        pk = 0.6 * dur
        e = np.where(t < pk, (t / pk) ** 2, np.exp(-(t - pk) / (0.12 * dur / 0.5)))
        x = bandpass(rng.standard_normal(n), 300, 3200 if kind == "whoosh" else 6000) * e
        return lowpass(x, 3500) * (0.5 if kind == "whoosh" else 0.32), pk
    if kind == "flash":
        a, _ = make_sfx("thock", rng)
        n = int(0.45 * SR); t = np.arange(n) / SR
        shim = bandpass(rng.standard_normal(n), 2500, 7000) * env(n, 0.01, 0.12) * 0.22
        out = np.zeros(n); out[:len(a)] += a * 0.8; out += shim
        return out, 0.0
    raise ValueError(kind)


def build_audio(work, out_wav):
    import soundfile as sf
    from scipy.signal import butter, sosfilt
    v, sr = sf.read(os.path.join(work, "voice.wav"), dtype="float32")
    if v.ndim > 1:
        v = v.mean(1)
    if sr != SR:
        from scipy.signal import resample_poly
        v = resample_poly(v, SR, sr).astype(np.float32)
    n = int(END * SR)
    v = np.pad(v, (0, max(0, n - len(v))))[:n]
    v = sosfilt(butter(2, 75, "high", fs=SR, output="sos"), v)
    v = v / (np.abs(v).max() + 1e-9) * 0.7
    fx = np.zeros(n)
    rng = np.random.default_rng(7)
    for t0, kind in SFX:
        x, pre = make_sfx(kind, rng)
        s = int((t0 - pre) * SR)
        if s < 0:
            x = x[-s:]; s = 0
        e = min(n, s + len(x))
        fx[s:e] += x[:e - s]
    fx *= 0.16   # sound effects sit well under the voice
    mix = np.stack([v + fx, v + fx], 1).astype(np.float32)
    sf.write(out_wav, mix, SR)


def loudnorm(src, dst):
    r = subprocess.run(f'ffmpeg -hide_banner -i "{src}" -af loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json -f null -',
                       shell=True, capture_output=True, text=True).stderr
    j = json.loads(r[r.rindex("{"):r.rindex("}") + 1])
    sh(f'ffmpeg -v error -y -i "{src}" -af "loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={j["input_i"]}:'
       f'measured_TP={j["input_tp"]}:measured_LRA={j["input_lra"]}:measured_thresh={j["input_thresh"]}:'
       f'offset={j["target_offset"]}:linear=true,aresample=48000" -ar 48000 "{dst}"')


# ===========================================================================
def _init(work):
    global R
    R = Renderer(work)


def _frame(fi):
    return R.frame(fi).tobytes()


def render(ref, work, only=None):
    from multiprocessing import Pool
    nfr = int(round(END * FPS))
    frames = range(nfr) if only is None else only
    if only is not None:   # stills for review
        _init(work)
        for fi in frames:
            Image.fromarray(R.frame(fi)).save(os.path.join(work, f"still_{fi:04d}.png"))
        return
    vid = os.path.join(work, "video.mp4")
    p = subprocess.Popen(f'ffmpeg -v error -y -f rawvideo -pix_fmt rgb24 -s {W}x{H} -r {FPS} -i - '
                         f'-c:v libx264 -preset slow -crf 16 -pix_fmt yuv420p "{vid}"', shell=True, stdin=subprocess.PIPE)
    with Pool(3, initializer=_init, initargs=(work,)) as pool:
        for k, buf in enumerate(pool.imap(_frame, frames, chunksize=4)):
            p.stdin.write(buf)
            if k % 150 == 0:
                print(f"frame {k}/{nfr}", flush=True)
    p.stdin.close(); p.wait()
    mix = os.path.join(work, "mix.wav"); master = os.path.join(work, "master.wav")
    build_audio(work, mix)
    loudnorm(mix, master)
    out = os.path.join(work, "AVE_Before_After.mp4")
    sh(f'ffmpeg -v error -y -i "{vid}" -i "{master}" -c:v copy -c:a aac -b:a 256k -shortest -movflags +faststart "{out}"')
    print(out)


if __name__ == "__main__":
    cmd, ref, work = sys.argv[1:4]
    if cmd == "prep":
        prep(ref, work)
    elif cmd == "render":
        render(ref, work)
    elif cmd == "stills":
        render(ref, work, only=[int(float(x) * FPS) for x in sys.argv[4:]])
