# Builds the 1080x960 top-panel track for the Reference-1 style reel (split screen
# for the whole video): influencer B-roll plus podcast cutaways (Cam B / Cam C)
# kept in sync with the edited audio.
# Usage: python3 build_top.py clip1
import json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import edit

S = edit.S
FPS = edit.FPS

# (source start s, source end s, what) - anchored to the original recording's time,
# so the top panel stays on the right words when cut points move. None = reel start/end.
#   what = ("cam", "B" | "C")  or  ("broll", file, source start s, vertical crop 0-1)
TOP = {
    "clip1": [
        (None, 364.864, ("cam", "B")),
        (364.864, 367.00, ("broll", "ivf_a", 21.0, 0.45)),
        (367.00, 369.055, ("cam", "C")),
        (369.055, 371.035, ("broll", "wedding_a", 52.0, 0.45)),
        (371.035, 374.295, ("broll", "ivf_b", 12.0, 0.15)),
        (374.295, 377.755, ("cam", "C")),
        (377.755, 389.47, ("cam", "B")),
        (389.47, 393.499, ("cam", "C")),
        (393.499, 452.118, ("cam", "B")),
        (452.118, 454.698, ("broll", "ivf_c", 23.9, 0.35)),
        (454.698, 457.718, ("broll", "ivf_a", 52.0, 0.3)),
        (457.718, 460.218, ("broll", "pilot_a", 0.5, 0.3)),
        (460.218, 468.81, ("broll", "poolguy", 7.6, 0.15)),
        (468.81, 471.255, ("broll", "test_b", 1.5, 0.7)),
        (471.255, 474.457, ("broll", "pregnant_a", 56.5, 0.65)),
        (474.457, None, ("broll", "kids_a", 41.8, 0.6)),
    ],
}


def src_to_out(timeline, t):
    """Output time of a source time; a time inside a removed gap maps to the next kept shot."""
    for s in timeline:
        if t < s["src_out"] - 1e-6:
            return s["out_in"] + max(0.0, t - s["src_in"])
    return sum(x["src_out"] - x["src_in"] for x in timeline)


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
    for i, (sa, sb, src) in enumerate(TOP[name]):
        fa = 0 if sa is None else fr(src_to_out(timeline, sa))
        fb = total_frames if sb is None else fr(src_to_out(timeline, sb))
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
