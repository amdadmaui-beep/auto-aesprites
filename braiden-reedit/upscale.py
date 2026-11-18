"""Real-ESRGAN (realesr-general-x4v3, SRVGGNetCompact) upscaler for the raw frames.

Usage: python upscale.py MODEL.pth SRC.mp4 OUT_DIR [crop=720:404:0:1]
Writes OUT_DIR/NNNN.jpg at 2x the crop size (x4 model, then downscaled for a clean result).
"""
import os, subprocess, sys
import numpy as np, torch, torch.nn as nn, cv2


class SRVGGNetCompact(nn.Module):
    def __init__(self, num_feat=64, num_conv=32, upscale=4):
        super().__init__()
        self.upscale = upscale
        body = [nn.Conv2d(3, num_feat, 3, 1, 1), nn.PReLU(num_parameters=num_feat)]
        for _ in range(num_conv):
            body += [nn.Conv2d(num_feat, num_feat, 3, 1, 1), nn.PReLU(num_parameters=num_feat)]
        body += [nn.Conv2d(num_feat, 3 * upscale * upscale, 3, 1, 1)]
        self.body = nn.ModuleList(body)
        self.up = nn.PixelShuffle(upscale)

    def forward(self, x):
        out = x
        for m in self.body:
            out = m(out)
        return self.up(out) + nn.functional.interpolate(x, scale_factor=self.upscale, mode="nearest")


def main(model_path, src, out_dir, crop="720:404:0:1"):
    os.makedirs(out_dir, exist_ok=True)
    torch.set_num_threads(4)
    net = SRVGGNetCompact()
    sd = torch.load(model_path, map_location="cpu")
    net.load_state_dict(sd.get("params", sd.get("params_ema", sd)), strict=True)
    net.eval()
    cw, ch = map(int, crop.split(":")[:2])
    raw = subprocess.run(f'ffmpeg -v error -i "{src}" -vf "crop={crop}" -f rawvideo -pix_fmt rgb24 -',
                         shell=True, check=True, capture_output=True).stdout
    frames = np.frombuffer(raw, np.uint8).reshape(-1, ch, cw, 3)
    for i, f in enumerate(frames, 1):
        o = os.path.join(out_dir, f"{i:04d}.jpg")
        if os.path.exists(o):
            continue
        x = torch.from_numpy(f.astype(np.float32) / 255).permute(2, 0, 1)[None]
        with torch.no_grad():
            y = net(x).clamp(0, 1)[0].permute(1, 2, 0).numpy()
        y = cv2.resize((y * 255).astype(np.uint8), (cw * 2, ch * 2), interpolation=cv2.INTER_AREA)
        cv2.imwrite(o, cv2.cvtColor(y, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 95])
        if i % 50 == 0:
            print(i, flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])
