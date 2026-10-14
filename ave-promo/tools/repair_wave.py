# Rebuild the two edges the board crops off the "happy" pose: the raised paw (left edge) and the left ear tip (top edge).
# Paw: mirrored from its own right half about the paw's centre line, tapering into the arm's outline.
# Ear: the cut rim is extended along its own edges to a rounded tip, texture resampled from the top rows.
import sys, numpy as np
from PIL import Image
src = np.array(Image.open(sys.argv[1]).convert('RGBA')).astype(np.float32)
H, W = src.shape[:2]; PL, PT = 90, 80
pre = src.copy(); pre[..., :3] *= src[..., 3:] / 255
out = np.zeros((H + PT, W + PL, 4), np.float32); out[PT:, PL:] = src
def S(x, y):  # bilinear sample of the source
    x = np.clip(x, 0, W - 1.001); y = np.clip(y, 0, H - 1.001); x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int); fx = (x - x0)[..., None]; fy = (y - y0)[..., None]
    v = (pre[y0, x0] * (1 - fx) * (1 - fy) + pre[y0, x0 + 1] * fx * (1 - fy) + pre[y0 + 1, x0] * (1 - fx) * fy + pre[y0 + 1, x0 + 1] * fx * fy)
    v[..., :3] /= np.maximum(v[..., 3:], 1e-3) / 255; return v
sm = lambda e0, e1, x: np.clip((x - e0) / (e1 - e0), 0, 1) ** 2 * (3 - 2 * np.clip((x - e0) / (e1 - e0), 0, 1))
# ---- paw: centre line x=45; left outline = mirror of the right outline, blending into the arm line (0,242)->(20,322)
AX = float(sys.argv[3]) if len(sys.argv) > 3 else 48.0
rows, Ls = [], []
for y in range(20, 250):
    row = src[y, :240, 3]; xs = np.where(row > 128)[0]
    if not len(xs) or xs.min() > 0: continue
    mirL = 2 * AX - min(xs.max(), 175)              # mirror of the paw's right outline
    armL = (y - 242) * .25                          # the arm's own left edge, extended
    k = sm(150, 238, y); rows.append(y); Ls.append(mirL * (1 - k) + armL * k)
Ls = np.array(Ls); Lp = np.pad(Ls, 7, mode='edge'); Ls = np.convolve(Lp, np.ones(15) / 15, 'valid')
for y, L in zip(rows, Ls):
    xn = np.arange(-PL, 0, dtype=np.float32)
    col = S(2 * AX - xn, np.full_like(xn, y))
    ke = sm(150, 236, y)                                # toward the wrist, continue the arm's own edge shading instead
    edge = src[y, 2:6].mean(0)
    col[:, :3] = col[:, :3] * (1 - ke) + edge[:3] * ke
    a = np.clip(xn - L + .5, 0, 1) * (col[:, 3] / 255)
    # rounded top of the outer toes: follow the mirrored alpha (keeps the toe gaps)
    col[:, 3] = a * 255
    out[PT + y, :PL] = col
    # cross-blend into the original over 24px so there is no seam, and match the original's shading
    xo = np.arange(0, 24, dtype=np.float32); mir = S(2 * AX - xo, np.full_like(xo, y)); org = src[y, :24].copy()
    k2 = 1 - (1 - sm(0, 24, xo)[:, None]) * (1 - sm(170, 236, y)); out[PT + y, PL:PL + 24, :3] = mir[:, :3] * (1 - k2) + org[:, :3] * k2
    out[PT + y, PL:PL + 24, 3] = np.maximum(org[:, 3], mir[:, 3] * (1 - k2[:, 0]))
# ---- ear: top row span 302..396; edges converge to a rounded tip ~70px above the cut
L0, R0 = 302.0, 396.0; tipx, tipy = 334.0, -68.0
for yy in range(-PT, 0):
    t = yy / tipy                                 # 0 at the cut, 1 at the tip
    if t >= 1: continue
    c = (L0 + R0) / 2 * (1 - t) + tipx * t
    hw = (R0 - L0) / 2 * (1 - t) ** .62           # rounded, not a spike
    xs = np.arange(int(c - hw) - 2, int(c + hw) + 3, dtype=np.float32)
    u = (xs - c) / max(hw, 1e-3)                  # -1..1 across the ear
    col = S((L0 + R0) / 2 + u * (R0 - L0) / 2, np.full_like(xs, 1.0 + 3 * t))
    a = np.clip((hw - np.abs(xs - c)) + .5, 0, 1) * col[:, 3] / 255
    col[:, 3] = a * 255
    out[PT + yy, PL + xs.astype(int)] = col
Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(sys.argv[2])
print(out.shape, 'pad', PL, PT)
# drop dark fringe specks the board crop left on the paw (the paw has no dark pixels of its own)
o = np.array(Image.open(sys.argv[2])).astype(np.float32)
reg = o[PT:PT + 250, :PL + 60]; lum = reg[..., :3].mean(-1); reg[(lum < 150) & (reg[..., 3] > 0), 3] = 0
Image.fromarray(o.astype(np.uint8)).save(sys.argv[2])
