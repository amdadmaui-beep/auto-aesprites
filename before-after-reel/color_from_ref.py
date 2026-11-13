"""Bring the creator's real colours back onto the clean B&W footage.

The reference shows the same moment twice: the raw B&W "Before" panel and a
colour "After" card that carries the other editor's text and graphics. We keep
our clean luminance (from the B&W panel) and only borrow chroma (skin, shirt)
from the colour card:

  1. register the colour card to the B&W panel every frame (SIFT + RANSAC),
  2. warp it into our upscaled source coordinates,
  3. reject pixels where the colour card's brightness disagrees with ours
     (that is where their text, icons and bubbles sit) and fill the chroma
     there from the surrounding skin / shirt,
  4. smooth over time, and save a small chroma map per frame.

Usage: python color_from_ref.py REF.mp4 WORK_DIR
Writes WORK_DIR/color2/NNNN.jpg: our clean footage carrying the reference's colour grade.
"""
import os, sys
import cv2
import numpy as np

SRC_W, SRC_H = 448, 1049          # our upscaled source (build_v2.py)
BX, BY, BW, BH = 81, 362, 199, 466  # B&W panel crop in the reference
AX, AY, AW, AH = 283, 290, 360, 640  # colour card in the reference
K = SRC_W / BW                      # 2.25


def register(B, A, sift, bf, cl):
    B2 = cv2.resize(B, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    kb, db = sift.detectAndCompute(cl.apply(B2), None)
    ka, da = sift.detectAndCompute(cl.apply(A), None)
    if db is None or da is None or len(kb) < 10 or len(ka) < 10:
        return None
    m = [a for a, b in (p for p in bf.knnMatch(db, da, k=2) if len(p) == 2) if a.distance < 0.75 * b.distance]
    if len(m) < 12:
        return None
    src = np.float32([kb[x.queryIdx].pt for x in m]) / 2
    dst = np.float32([ka[x.trainIdx].pt for x in m])
    M, inl = cv2.estimateAffinePartial2D(src, dst, method=cv2.RANSAC, ransacReprojThreshold=3)
    if M is None or inl.sum() < 25:
        return None
    s = np.hypot(M[0, 0], M[1, 0])
    if not 1.1 < s < 1.5 or abs(M[1, 0]) > 0.05 * s:
        return None
    return np.array([s, M[0, 2], M[1, 2]])


def main(ref, work):
    out = os.path.join(work, "chroma"); os.makedirs(out, exist_ok=True)
    cap = cv2.VideoCapture(ref)
    frames = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        frames.append(f)
    n = len(frames)
    sift, bf, cl = cv2.SIFT_create(2500), cv2.BFMatcher(), cv2.createCLAHE(2.0, (8, 8))
    P = [None] * n
    for i, f in enumerate(frames):
        B = cv2.cvtColor(f[BY:BY + BH, BX:BX + BW], cv2.COLOR_BGR2GRAY)
        A = cv2.cvtColor(f[AY:AY + AH, AX:AX + AW], cv2.COLOR_BGR2GRAY)
        P[i] = register(B, A, sift, bf, cl)
    valid = [i for i in range(n) if P[i] is not None]
    print(f"registered {len(valid)}/{n} frames", flush=True)
    # temporal median of the transform (5 frames) on valid frames
    Ps = {}
    for i in valid:
        win = [P[j] for j in range(i - 2, i + 3) if 0 <= j < n and P[j] is not None]
        Ps[i] = np.median(np.stack(win), 0)

    out_c = os.path.join(work, "color2"); os.makedirs(out_c, exist_ok=True)
    sm = lambda x, sg: cv2.GaussianBlur(x, (0, 0), sg)
    coefs = {}
    for i in valid:
        s, tx, ty = Ps[i]
        # our source pixel p -> B coords p/K -> A coords s*(p/K) + t
        M = np.float32([[s / K, 0, tx], [0, s / K, ty]])
        Acol = frames[i][AY:AY + AH, AX:AX + AW]
        warped = cv2.warpAffine(Acol, M, (SRC_W, SRC_H), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP)
        inside = cv2.warpAffine(np.full((AH, AW), 255, np.uint8), M, (SRC_W, SRC_H),
                                flags=cv2.INTER_NEAREST | cv2.WARP_INVERSE_MAP) > 0
        lab = cv2.cvtColor(warped, cv2.COLOR_BGR2LAB).astype(np.float32)
        L, a, b = lab[..., 0], lab[..., 1] - 128, lab[..., 2] - 128
        chroma = np.hypot(a, b)
        # their overlays: white text / bubbles, saturated purple pills and words
        text = ((L > 195) & (chroma < 28)) | (chroma > 40)
        text = cv2.dilate(text.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
        person = cv2.imread(os.path.join(work, "mask2", f"{i + 1:04d}.png"), cv2.IMREAD_GRAYSCALE)
        person = cv2.dilate((person > 100).astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
        w = (inside & ~text & person).astype(np.float32)
        g = cv2.imread(os.path.join(work, "after2", f"{i + 1:04d}.png"), cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255

        def fit_(sig):
            sw = sm(w, sig) + 1e-5
            mg = sm(w * g, sig) / sw
            vg = sm(w * g * g, sig) / sw - mg * mg
            cs = []
            for c in (L / 255, a / 255, b / 255):
                mc = sm(w * c, sig) / sw
                cov = sm(w * g * c, sig) / sw - mg * mc
                A_ = cov / (vg + 2e-3)
                cs += [A_, mc - A_ * mg]
            return np.stack(cs, -1), sw
        Cf, swf = fit_(10)
        Cc, swc = fit_(45)
        conf = np.clip(swf / 0.35, 0, 1)[..., None]
        C = Cf * conf + Cc * (1 - conf)
        coefs[i] = np.dstack([sm(C[..., k], 6) for k in range(6)]).astype(np.float32)
    last = None
    for i in range(n):
        win = [coefs[j] for j in range(i - 2, i + 3) if j in coefs]
        if win:
            last = np.mean(np.stack(win), 0)
        C = last if last is not None else coefs[valid[0]]
        g = cv2.imread(os.path.join(work, "after2", f"{i + 1:04d}.png"), cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255
        L = (C[..., 0] * g + C[..., 1]) * 255
        a = (C[..., 2] * g + C[..., 3]) * 255
        b = (C[..., 4] * g + C[..., 5]) * 255
        # tame the reference's purple light spill into a neutral, slightly cool tone
        purp = np.clip((a - 4) / 20, 0, 1) * np.clip((-b - 6) / 20, 0, 1)
        a = a * (1 - 0.8 * purp)
        lab = np.dstack([np.clip(L, 0, 255), np.clip(a + 128, 0, 255), np.clip(b + 128, 0, 255)]).astype(np.uint8)
        cv2.imwrite(os.path.join(out_c, f"{i + 1:04d}.jpg"), cv2.cvtColor(lab, cv2.COLOR_LAB2BGR),
                    [cv2.IMWRITE_JPEG_QUALITY, 95])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
