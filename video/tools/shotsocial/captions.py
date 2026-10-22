# Turns hand-checked caption lines into timed JSON for the Remotion reel.
# Each line is (text, number of transcript words it covers). Extra lines can be
# pinned to a time with ("text", None, start, end).
import json, re, sys

FPS = 24000 / 1001

LINES = {
    "clip1": {
        "title": ["HOW FANTASY", "HELPED HER CLIENTS", "GET PREGNANT 🤯"],
        "lines": [
            ("And I actually found it by mistake", 7),
            ("because I work a lot", 5),
            ("with infertile people.", 3),
            ("One of my clients saying,", 5),
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
            ("was a pilot or the pool guy", 7),
            ("or anything.", 2),
            ("And they all said,", 4),
            ("“Well, we got pregnant so quickly,", 6),
            ("we gave up IVF.”", 4),
            ("It was just playing that game.", 6),
            ("But now we've got the children,", 6),
            ("we're still doing it.", 4),
            ("It's still fantastic.", 3),
        ],
    },
    "clip2": {
        "title": ["WHY THINKING", "ABOUT CAKE MAKES", "YOU GAIN WEIGHT 🍰"],
        "lines": [
            ("My mother was always on a diet.", 7),
            ("Everything in our fridge was", 5),
            ("diet yogurt, diet milk, diet shakes,", 6),
            ("so you pretty much", 4),
            ("learn what you live.", 4),
            ("And so I began many, many years", 7),
            ("of dieting.", 2),
            ("After years of dieting,", 4),
            ("my weight stayed exactly the same.", 6),
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
    total = sum(s["src_out"] - s["src_in"] for s in timeline)
    # Hold each line until the next one starts (no flicker between lines), max 0.6 s extra.
    for a, b in zip(caps, caps[1:]):
        a["end"] = b["start"] if b["start"] - a["end"] < 0.6 else a["end"] + 0.3
    caps[-1]["end"] = total
    split_end = sum(s["src_out"] - s["src_in"] for s in timeline if s["mode"] == "split")
    data = {
        "fps": FPS, "durationInFrames": round(total * FPS), "title": spec["title"], "splitEnd": split_end,
        "captions": [{"text": c["text"], "from": round(c["start"] * FPS), "to": round(c["end"] * FPS)} for c in caps],
    }
    json.dump(data, open(f"{out_dir}/{name}.json", "w"), indent=1, ensure_ascii=False)
    print(name, len(caps), "lines,", round(total, 2), "s, longest line:",
          max(len(c["text"]) for c in caps), "chars")


if __name__ == "__main__":
    for n in ("clip1", "clip2"):
        build(n, sys.argv[1], sys.argv[2])
