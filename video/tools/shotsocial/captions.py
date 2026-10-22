# Turns hand-checked caption lines into timed JSON for the Remotion reel.
# Each line is (text, number of transcript words it covers). Extra lines can be
# pinned to a time with ("text", None, start, end).
import json, re, sys

FPS = 24000 / 1001

LINES = {
    "clip1": {
        # VIDEO SAMPLE 1: split screen for the whole reel; the top panel is
        # pre-built by build_top.py (B-roll + podcast cutaways).
        "layout": "ref1",
        "title_end": "src:367.00",  # first subtitle ("And then one of my clients saying,")
        "broll": [],
        "title": ["HOW FANTASY", "HELPED HER CLIENTS", "GET PREGNANT 🤯"],
        "lines": [
            ("And I actually found it by mistake", 7),
            ("because I work a lot", 5),
            ("with infertile people.", 3),
            ("And then one of my clients saying,", 7),
            ("“I'm going to call off my wedding", 7),
            ("because my husband's got", 4),
            ("a very low sperm count", 5),
            ("and we can't have children.”", 5),
            ("I said, you know,", 4),
            ("every time a man has sex", 6),
            ("with a new person,", 4),
            ("his sperm output trebles.", 4),
            ("Wow.", None, "shot4"),
            ("And so if a man can fantasize", 7),
            ("about being with a new woman,", 6),
            ("he will treble the amount", 5),
            ("of sperm he ejaculates.", 4),
            ("And so I found this as a way", 8),
            ("to help my clients", 4),
            ("who couldn't conceive", 3),
            ("fantasize their husband", 3),
            ("was a pilot or a pool guy", 7),
            ("or anything.", 2),
            ("And they all said,", 4),
            ("“Wow, we got pregnant so quickly,", 6),
            ("we gave up IVF.”", 4),
            ("It was just playing that game.", 6),
            ("And now we've got the children,", 6),
            ("we're still doing it.", 4),
            ("It's still fantastic.", 3),
        ],
    },
    "clip2": {
        # VIDEO SAMPLE 2: split hook with a product close-up below, then a burst of
        # full-screen B-roll, then clean podcast.
        # B-roll: (file, output start s, output end s, source start s, vertical crop %).
        "layout": "ref2",
        "hook_bottom": ("cake_a", 0.0, 40),
        # B-roll: (file, output start s, output end s, source start s, vertical crop %, zoom).
        "broll": [("fridge_a", None, "src:1154.482", 45.0, 50, 1), ("yogurt_b", "src:1154.482", "src:1156.182", 0.2, 0, 1.35),
                  ("milk_a", "src:1156.182", "src:1157.202", 14.6, 50, 1), ("slimfast_a", "src:1157.202", "src:1158.16", 16.6, 50, 1)],
        "title": ["WHY THINKING", "ABOUT CAKE MAKES", "YOU GAIN WEIGHT 🍰"],
        "lines": [
            ("My mother was always on a diet.", 7),
            ("Everything in our fridge was", 5),
            ("diet yogurt,", 2),
            ("diet milk,", 2),
            ("diet shakes,", 2),
            ("so pretty much", 3),
            ("learn what you live.", 4),
            ("And so I began many, many years", 7),
            ("of dieting.", 2),
            ("After years of dieting,", 4),
            ("my weight stayed exactly the same.", 6),
            ("I can wear whatever I want.", 6),
            ("I just wasted 15 years", 5),
            ("because I didn't understand", 4),
            ("that your psychology is having", 4),
            ("a full-on conversation", 4),
            ("with your biology.", 3),
            ("“I can't eat that or I'll get fat”", 8),
            ("becomes your reality.", 3),
            ("Actually, if you say,", 4),
            ("“I get fat just looking at a cake,”", 8),
            ("do you know that thought", 5),
            ("creates cortisol,", 2),
            ("and cortisol makes you gain weight.", 6),
            ("So it's true that you can say,", 7),
            ("“I can gain weight", 5),
            ("just thinking about cake.”", 4),
            ("Also true that you can be", 6),
            ("a perfect weight while eating cake.", 6),
        ],
    },
}


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower().replace("'", "'"))


def src_out(timeline, b):
    """Output seconds; "src:<t>" anchors to a source time (survives moved cuts)."""
    if not str(b).startswith("src:"):
        return b
    t = float(b[4:])
    for s in timeline:
        if t < s["src_out"] - 1e-6:
            return s["out_in"] + max(0.0, t - s["src_in"])


def onsets(path):
    """Speech onsets (s) in the final edited audio: quiet for 40 ms, then loud."""
    import wave
    import numpy as np
    wf = wave.open(path); sr = wf.getframerate(); ch = wf.getnchannels()
    x = np.frombuffer(wf.readframes(wf.getnframes()), np.int16).astype(np.float32) / 32768
    x = x.reshape(-1, ch).mean(1)
    h = sr // 100; n = len(x) // h
    e = 20 * np.log10(np.sqrt((x[:n * h].reshape(n, h) ** 2).mean(1) + 1e-12))
    loud = e > -32
    return [i / 100 for i in range(4, n) if loud[i] and not loud[i - 1] and (e[i - 4:i] < -36).all()]


def snap_to_onset(t, ons, before=0.35, after=0.2):
    """Move a subtitle start onto the nearest real speech onset, if there is one close by."""
    near = [o for o in ons if t - before <= o <= t + after]
    return min(near, key=lambda o: abs(o - t)) - 0.02 if near else t


def build(name, scratch, out_dir):
    words = json.load(open(f"{scratch}/{name}_outwords.json"))
    timeline = json.load(open(f"{scratch}/build/{name}/timeline.json"))
    spec = LINES[name]
    caps, i = [], 0
    for line in spec["lines"]:
        text, n = line[0], line[1]
        if n is None:
            shot = timeline[int(line[2][4:])]
            caps.append({"text": text, "start": shot["out_in"] + 0.15,
                         "end": shot["out_in"] + shot["src_out"] - shot["src_in"]})
            continue
        ws = words[i:i + n]
        i += n
        # Sanity check: the caption must contain the same words (fillers like "if" may be dropped).
        heard = [norm(w[2]) for w in ws]
        said = norm(text.replace("full-on", "full on").replace("output", "outtake"))
        miss = [h for h in heard if h not in said and h not in ("if",)]
        if miss:
            print(f"!! {name}: '{text}' vs {[w[2] for w in ws]}")
        caps.append({"text": text, "start": ws[0][0], "end": ws[-1][1]})
    assert i == len(words), f"{name}: used {i} of {len(words)} words"
    caps.sort(key=lambda c: c["start"])
    # Subtitles appear when the words are actually heard, not when the transcript says.
    ons = onsets(f"{scratch}/build/{name}/audio.wav")
    moved = []
    for c in caps:
        new = snap_to_onset(c["start"], ons)
        moved.append(new - c["start"]); c["start"] = new
    print(name, "subtitle starts snapped to audio onsets:", sum(1 for m in moved if m), "of", len(caps),
          "| mean shift", round(sum(moved) / len(moved) * 1000), "ms")
    total = sum(s["src_out"] - s["src_in"] for s in timeline)
    # Hold each line until the next one starts (no flicker between lines), max 0.6 s extra.
    for a, b in zip(caps, caps[1:]):
        a["end"] = b["start"] if b["start"] - a["end"] < 0.6 else a["end"] + 0.3
    caps[-1]["end"] = total
    split_end = src_out(timeline, spec["title_end"]) if "title_end" in spec else sum(s["src_out"] - s["src_in"] for s in timeline if s["mode"] == "split")
    data = {
        "fps": FPS, "durationInFrames": round(total * FPS), "title": spec["title"], "splitEnd": split_end,
        "layout": spec["layout"],
        "hookBottom": ({"file": spec["hook_bottom"][0], "srcFrom": round(spec["hook_bottom"][1] * FPS),
                        "posY": spec["hook_bottom"][2]} if "hook_bottom" in spec else None),
        "broll": [{"file": f, "from": round((split_end if a is None else src_out(timeline, a)) * FPS),
                   "to": round((total if b is None else src_out(timeline, b)) * FPS), "srcFrom": round(src * FPS), "posY": pos, "zoom": zoom}
                  for f, a, b, src, pos, zoom in spec["broll"]],
        "captions": [{"text": c["text"], "from": round(c["start"] * FPS), "to": round(c["end"] * FPS)} for c in caps],
    }
    json.dump(data, open(f"{out_dir}/{name}.json", "w"), indent=1, ensure_ascii=False)
    print(name, len(caps), "lines,", round(total, 2), "s, longest line:",
          max(len(c["text"]) for c in caps), "chars")


if __name__ == "__main__":
    for n in ("clip1", "clip2"):
        build(n, sys.argv[1], sys.argv[2])
