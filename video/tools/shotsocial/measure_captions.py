# Caption metrics from a frame: text box (normalised to frame width), stroke width,
# and how much the shadow darkens the background at each distance from the letters.
import sys, numpy as np, cv2
def measure(path, y0, y1, label):
    img = cv2.imread(path); H, W = img.shape[:2]; s = W / 1080.0
    roi = img[int(y0 * s):int(y1 * s)].astype(np.float32)
    lum = roi.mean(2)
    white = (roi.min(2) > 225).astype(np.uint8)
    # keep the caption line: biggest band of rows with white pixels
    rows = np.where(white.sum(1) > 2)[0]; cols = np.where(white.sum(0) > 0)[0]
    if not len(rows): print(label, "no text"); return
    x0, x1, t, b = cols.min(), cols.max(), rows.min(), rows.max()
    # horizontal stroke runs inside the glyphs
    runs = []
    for r in range(t, b + 1):
        row = white[r].astype(int); d = np.diff(np.r_[0, row, 0]); st = np.where(d == 1)[0]; en = np.where(d == -1)[0]
        runs += list(en - st)
    runs = np.array(runs); stroke = np.median(runs[(runs > 1) & (runs < 0.04 * W)]) / s
    dist = cv2.distanceTransform(1 - white, cv2.DIST_L2, 3) / s   # in 1080-scale px
    far = lum[(dist > 30) & (dist < 45)]; bg = np.median(far)
    prof = []
    for d in (2, 4, 6, 9, 12, 16, 20, 25):
        ring = lum[(dist > d - 1) & (dist <= d + 1)]
        prof.append(np.median(ring) / bg)
    print(f"{label}: width {(x1-x0)/W*100:.1f}% of frame, text height {(b-t)/s:.0f}px@1080, "
          f"stroke {stroke:.1f}px@1080, bg lum {bg:.0f}")
    print("   shadow (lum/bg) at 2,4,6,9,12,16,20,25px:", " ".join(f"{p:.2f}" for p in prof))
for a in sys.argv[1:]:
    p, y0, y1, l = a.split(":"); measure(p, float(y0), float(y1), l)

def offset(path, y0, y1, label):
    """Shadow darkness just above vs just below the text, and left vs right."""
    img = cv2.imread(path); H, W = img.shape[:2]; s = W / 1080.0
    roi = img[int(y0 * s):int(y1 * s)].astype(np.float32); lum = roi.mean(2)
    white = (roi.min(2) > 225).astype(np.uint8)
    dist = cv2.distanceTransform(1 - white, cv2.DIST_L2, 3) / s
    ys, xs = np.where(white > 0); cy, cx = ys.mean(), xs.mean()
    far = np.median(lum[(dist > 30) & (dist < 45)])
    band = (dist > 3) & (dist < 12)
    yy, xx = np.mgrid[0:lum.shape[0], 0:lum.shape[1]]
    up = np.median(lum[band & (yy < ys.min() + 2)]) / far
    dn = np.median(lum[band & (yy > ys.max() - 2)]) / far
    print(f"{label}: above-text {up:.2f}  below-text {dn:.2f}  (lower = darker)")
