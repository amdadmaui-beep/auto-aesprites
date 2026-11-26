# Inflated lime 3D letters from the AVE wordmark: distance-field height map + Phong shading.
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage as nd
src = Image.open('img/ave-wordmark-black.png').convert('RGBA')
S = 2.0
src = src.resize((int(src.width*S), int(src.height*S)), Image.LANCZOS)
pad = 120
a = np.array(src)[..., 3].astype(np.float32) / 255
a = np.pad(a, pad)
m = a > 0.5
lab, n = nd.label(m)
print('components', n)
R = 125.0
def shade(mask):
    d = nd.distance_transform_edt(mask)
    t = np.clip(d / R, 0, 1)
    h = R * np.sqrt(1 - (1 - t) ** 2)
    h = nd.gaussian_filter(h, 5.0)
    gy, gx = np.gradient(h)
    nz = np.ones_like(h)
    nrm = np.sqrt(gx**2 + gy**2 + nz**2)
    nx, ny, nz = -gx/nrm, -gy/nrm, nz/nrm
    L = np.array([-0.45, -0.6, 0.66]); L /= np.linalg.norm(L)
    lam = np.clip(nx*L[0] + ny*L[1] + nz*L[2], 0, 1)
    H = L + np.array([0, 0, 1.0]); H /= np.linalg.norm(H)
    spec = np.clip(nx*H[0] + ny*H[1] + nz*H[2], 0, 1) ** 25
    # inner bevel line like the reference (a thin ridge a little inside the edge)
    ridge = np.exp(-((d - 14) / 3.5) ** 2) * 0.25
    base = np.array([200, 255, 46], np.float32) / 255      # brand lime #c8ff2e
    dark = np.array([96, 170, 10], np.float32) / 255
    yy = np.linspace(0, 1, h.shape[0])[:, None]
    col = dark[None, None] * (1 - lam[..., None]) + base[None, None] * lam[..., None]
    col = col * (0.92 + 0.12 * (1 - yy))[..., None]
    col = col + spec[..., None] * 0.85 + ridge[..., None] * np.array([1, 1, 0.85])
    # soft white sheen in the middle (the reference letters fade to white inside)
    sheen = np.clip((t - 0.55) / 0.45, 0, 1) ** 1.5 * 0.55
    col = col * (1 - sheen[..., None]) + sheen[..., None]
    col = np.clip(col, 0, 1)
    alpha = nd.gaussian_filter(mask.astype(np.float32), 1.0)
    return col, alpha
out = []
for i in range(1, n + 1):
    mk = lab == i
    ys, xs = np.where(mk)
    if len(xs) < 500: continue
    col, al = shade(mk)
    rgba = np.dstack([col, al]) * 255
    im = Image.fromarray(rgba.astype(np.uint8), 'RGBA')
    out.append((xs.min(), im))
out.sort(key=lambda x: x[0])
W, Hh = out[0][1].size
for k, (x0, im) in enumerate(out):
    im.save(f'img/blob_{k}.png')
full = Image.new('RGBA', (W, Hh))
for _, im in out: full = Image.alpha_composite(full, im)
bb = full.getbbox(); print('size', full.size, 'bbox', bb, 'pad', pad)
full.save('img/blob_full.png')
