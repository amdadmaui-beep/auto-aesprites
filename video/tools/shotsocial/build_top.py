# Builds the 1080x960 top-panel track for the Reference-1 style reel (split screen
# for the whole video): influencer B-roll plus podcast cutaways (Cam B / Cam C)
# kept in sync with the edited audio.
# Usage: python3 build_top.py clip1
import json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import edit

S = edit.S
FPS = edit.FPS

# (output start s, output end s, source) where source is
#   ("cam", "B" | "C")  or  ("broll", file, source start s, vertical crop 0-1)
TOP = {
    "clip1": [
        (0.00, 1.71, ("cam", "B")),
        (1.71, 3.80, ("broll", "ivf_a", 21.0, 0.45)),
        (3.80, 4.90, ("cam", "C")),
        (4.90, 6.88, ("broll", "wedding_a", 52.0, 0.45)),
        (6.88, 10.14, ("broll", "ivf_b", 12.0, 0.15)),
        (10.14, 13.60, ("cam", "C")),
        (13.60, 16.69, ("cam", "B")),
        (16.69, 20.71, ("cam", "C")),
        (20.71, 23.19, ("cam", "B")),
        (23.19, 25.77, ("broll", "ivf_c", 23.9, 0.35)),
        (25.77, 28.79, ("broll", "ivf_a", 52.0, 0.3)),
        (28.79, 31.29, ("broll", "pilot_a", 0.5, 0.3)),
        (31.29, 33.12, ("broll", "poolguy", 7.6, 0.15)),
        (33.12, 35.57, ("broll", "test_b", 1.5, 0.7)),
        (35.57, 38.23, ("broll", "pregnant_a", 56.5, 0.65)),
        (38.23, None, ("broll", "kids_a", 41.8, 0.6)),
    ],
}

# Wide two-shot crop from Cam C (both women, 9:8).
CAM_C = "crop=2000:1778:980:300,scale=1080:960:flags=lanczos"


def fr(t):
    return round(t * FPS)


def main(name):
    work = f"{S}/build/{name}/top"
    os.makedirs(work, exist_ok=True)
    timeline = json.load(open(f"{S}/build/{name}/timeline.json"))
    total_frames = sum(fr(s["src_out"] - s["src_in"]) for s in timeline)
    # Output frame -> source time, from the edit timeline.
    bounds, f0 = [], 0
    for s in timeline:
        n = fr(s["src_out"] - s["src_in"])
        bounds.append((f0, f0 + n, s["src_in"]))
        f0 += n
    faces = {}
    parts = []
    for i, (a, b, src) in enumerate(TOP[name]):
        fa, fb = fr(a), (total_frames if b is None else fr(b))
        pieces = []
        if src[0] == "broll":
            _, f, ss, py = src
            vf = (f"scale=1080:960:force_original_aspect_ratio=increase:flags=lanczos,"
                  f"crop=1080:960:(iw-1080)/2:(ih-960)*{py},fps={FPS},trim=end_frame={fb - fa},setsar=1")
            pieces.append((["-ss", f"{ss}", "-t", f"{(fb - fa) / FPS + 1}", "-i", f"{S}/broll/{f}.mp4"], vf))
        else:
            cam = src[1]
            # Split at edit cut points so lips stay in sync with the jump-cut audio.
            for (s0, s1, sin) in bounds:
                lo, hi = max(fa, s0), min(fb, s1)
                if lo >= hi:
                    continue
                t0 = sin + (lo - s0) / FPS
                n = hi - lo
                if cam == "C":
                    crop = CAM_C
                else:
                    key = f"{t0:.2f}"
                    if key not in faces:
                        faces[key] = edit.face("B", t0, t0 + n / FPS)
                    crop = edit.crop_for("B", "split", *faces[key], 1080, 960, 0.42)
                vf = f"{crop},fps={FPS},trim=end_frame={n},setsar=1"
                pieces.append((["-ss", f"{t0}", "-t", f"{n / FPS + 0.5}", "-i", f"{edit.RAW}/Cam_{cam}.mp4"], vf))
        for j, (inp, vf) in enumerate(pieces):
            out = f"{work}/p{i:02d}_{j}.mp4"
            subprocess.run(["ffmpeg", "-v", "error", "-y", *inp, "-vf", vf, "-an", "-c:v", "libx264",
                            "-crf", "15", "-preset", "fast", "-pix_fmt", "yuv420p", out], check=True)
            parts.append(out)
        print(name, i, src[:2], fa, fb, flush=True)
    with open(f"{work}/list.txt", "w") as f:
        f.writelines(f"file '{p}'\n" for p in parts)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", f"{work}/list.txt",
                    "-c", "copy", f"{S}/build/{name}/top.mp4"], check=True)
    n = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                        "stream=nb_read_frames", "-of", "csv=p=0", f"{S}/build/{name}/top.mp4"],
                       capture_output=True, text=True).stdout.strip()
    print(name, "top frames", n, "expected", total_frames)


if __name__ == "__main__":
    main(sys.argv[1])
