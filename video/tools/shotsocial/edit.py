# Builds the base video (cuts, framing, audio) for each reel.
# Usage: python3 -I edit.py <clip1|clip2>
import json, subprocess, sys, os
import cv2, numpy as np

S = os.path.dirname(os.path.abspath(__file__))
RAW = f"{S}/raw"
FPS = 24000 / 1001

# (src_in, src_out, cam, mode)  mode: split | wide | punch
CLIPS = {
    "clip1": [
        (363.10, 366.95, "A", "wide"),
        (366.95, 370.15, "A", "punch"),
        (370.15, 374.28, "A", "wide"),
        (374.28, 379.60, "A", "wide"),
        (379.60, 380.70, "A", "punch"),
        (389.47, 395.67, "A", "wide"),
        (452.00, 457.30, "A", "punch"),
        (457.30, 462.16, "A", "wide"),
        (468.82, 470.90, "A", "punch"),
        (470.90, 472.40, "A", "wide"),
        (472.85, 474.30, "A", "wide"),
        (474.30, 477.66, "A", "punch"),
    ],
    "clip2": [
        (1151.61, 1153.30, "AB", "split"),
        (1153.30, 1155.00, "A", "wide"),
        (1155.00, 1158.80, "A", "punch"),
        (1159.90, 1161.18, "A", "wide"),
        (1168.40, 1169.82, "A", "punch"),
        (1170.00, 1171.45, "A", "wide"),
        (1172.25, 1173.12, "A", "punch"),
        (1200.90, 1204.48, "A", "punch"),
        (1204.48, 1210.35, "A", "wide"),
        (1210.80, 1213.10, "A", "punch"),
        (1213.10, 1216.70, "A", "wide"),
        (1228.50, 1232.40, "A", "punch"),
        (1232.40, 1237.25, "A", "wide"),
        (1237.93, 1241.23, "B", "punch"),
        (1241.82, 1246.83, "A", "punch"),
    ],
}

# Eye height in the 4K source (measured from sample frames).
EYE_Y = {"A": 800, "B": 640}
FRONT = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
PROF = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_profileface.xml")
DEFAULT_X = {"A": 2000, "B": 1450}


def face(cam, t0, t1):
    """Median face centre (x, eye y) over the shot, in 4K pixels."""
    xs, ys = [], []
    t = t0 + 0.2
    while t < t1:
        out = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", f"{RAW}/Cam_{cam}.mp4",
                              "-frames:v", "1", "-vf", "scale=960:540", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                             capture_output=True).stdout
        g = np.frombuffer(out, np.uint8).reshape(540, 960)
        best = None
        for c in (FRONT, PROF):
            for img, flip in ((g, False), (cv2.flip(g, 1), True)):
                f = c.detectMultiScale(img, 1.1, 5, minSize=(60, 60))
                for (x, y, w, h) in f:
                    if flip:
                        x = 960 - x - w
                    if best is None or w > best[2]:
                        best = (x, y, w, h)
            if best is not None:
                break
        if best is not None:
            x, y, w, h = best
            xs.append((x + w / 2) * 4)
            ys.append((y + h * 0.42) * 4)
        t += 0.6
    if not xs:
        return DEFAULT_X[cam], EYE_Y[cam]
    return float(np.median(xs)), float(np.median(ys))


def crop_for(cam, mode, fx, ey, out_w, out_h, eye_frac):
    if mode == "wide":
        h = 2160
    elif mode == "punch":
        h = 1780
    else:  # split half
        h = 1500 if cam == "A" else 1400
    if cam == "B" and mode != "split":
        h = min(h, int(ey / eye_frac))  # keep B's eye line level with A's
    w = int(round(h * out_w / out_h))
    x = int(min(max(fx - w / 2, 0), 3840 - w))
    y = int(min(max(ey - eye_frac * h, 0), 2160 - h))
    return f"crop={w}:{h}:{x}:{y},scale={out_w}:{out_h}:flags=lanczos"


def audio_runs(name):
    """Exact source audio ranges, one per run of shots that play continuous source.

    Picture cuts sit on the frame grid; audio cuts sit on the exact measured word
    boundary. Each run keeps the total length of its shots and ends exactly at the
    requested out point, so lip sync moves by at most half a frame (21 ms) and the
    audio never jumps inside a continuous take.
    """
    runs, start = [], 0
    clip = CLIPS[name]
    for i in range(len(clip)):
        last = i == len(clip) - 1
        if last or abs(snap(clip[i][1]) - snap(clip[i + 1][0])) > 1e-6:
            dur = sum(snap(b) - snap(a) for a, b, *_ in clip[start:i + 1])
            runs.append((clip[i][1] - dur, clip[i][1]))
            start = i + 1
    return runs


def snap(t):
    return round(round(t * FPS) / FPS, 6)


def main(name):
    # Snap cut points to the frame grid so picture and sound stay in sync.
    shots = [(snap(a), snap(b), c, m) for a, b, c, m in CLIPS[name]]
    work = f"{S}/build/{name}"
    os.makedirs(work, exist_ok=True)
    cache = f"{work}/faces.json"
    faces = json.load(open(cache)) if os.path.exists(cache) else {}
    parts = []
    for i, (a, b, cam, mode) in enumerate(shots):
        cams = ["A", "B"] if cam == "AB" else [cam]
        for c in cams:
            k = f"{c}:{a}:{b}"
            if k not in faces:
                faces[k] = face(c, a, b)
                print(name, i, c, faces[k], flush=True)
        json.dump(faces, open(cache, "w"))
        out = f"{work}/shot{i:02d}.mp4"
        parts.append(out)
        dur = b - a
        if mode == "split":
            fa, fb = faces[f"A:{a}:{b}"], faces[f"B:{a}:{b}"]
            vf = (f"[0:v]{crop_for('A', 'split', *fa, 1080, 960, 0.42)}[t];"
                  f"[1:v]{crop_for('B', 'split', *fb, 1080, 960, 0.42)}[u];[t][u]vstack,fps={FPS},trim=end_frame={round(dur * FPS)}[v]")
            inputs = ["-ss", f"{a}", "-t", f"{dur + 0.5}", "-i", f"{RAW}/Cam_A.mp4",
                      "-ss", f"{a}", "-t", f"{dur + 0.5}", "-i", f"{RAW}/Cam_B.mp4"]
        else:
            vf = f"[0:v]{crop_for(cam, mode, *faces[f'{cam}:{a}:{b}'], 1080, 1920, 0.365)},fps={FPS},trim=end_frame={round(dur * FPS)}[v]"
            inputs = ["-ss", f"{a}", "-t", f"{dur + 0.5}", "-i", f"{RAW}/Cam_{cam}.mp4"]
        subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", vf, "-map", "[v]",
                        "-an", "-c:v", "libx264", "-crf", "14", "-preset", "fast", "-pix_fmt", "yuv420p", out],
                       check=True)
    # Video: concat shots.
    with open(f"{work}/list.txt", "w") as f:
        f.writelines(f"file '{p}'\n" for p in parts)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", f"{work}/list.txt",
                    "-c", "copy", f"{work}/video.mp4"], check=True)
    # Audio: both mics summed, same cuts, 15 ms fades at every cut, loudness to -14 LUFS.
    fl = []
    runs = audio_runs(name)
    for i, (a, b) in enumerate(runs):
        d = b - a
        fo = 0.06 if i == len(runs) - 1 else 0.015  # softer ending on the last word
        fl.append(f"[m{i}]atrim={a}:{b},asetpts=PTS-STARTPTS,afade=t=in:d=0.015,"
                  f"afade=t=out:st={d - fo:.3f}:d={fo}[s{i}]")
    n = len(fl)
    fc = (f"[0:a][1:a]amix=inputs=2:normalize=0,asplit={n}" + "".join(f"[m{i}]" for i in range(n)) + ";"
          + ";".join(fl) + ";" + "".join(f"[s{i}]" for i in range(n))
          + f"concat=n={n}:v=0:a=1,loudnorm=I=-14:TP=-1:LRA=11[a]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f"{RAW}/Audio_1.wav", "-i", f"{RAW}/Audio_2.wav",
                    "-filter_complex", fc, "-map", "[a]", "-ar", "48000", "-c:a", "pcm_s16le", f"{work}/audio.wav"],
                   check=True)
    # Timeline map for captions: output start of each shot.
    tl, t = [], 0.0
    for (a, b, cam, mode) in shots:
        tl.append({"src_in": a, "src_out": b, "out_in": t, "cam": cam, "mode": mode})
        t += b - a
    json.dump(tl, open(f"{work}/timeline.json", "w"), indent=1)
    print(name, "done", round(t, 2), "s")


if __name__ == "__main__":
    main(sys.argv[1])
