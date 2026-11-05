#!/usr/bin/env python3
"""AVE lead radar: finds fresh "looking for an editor" posts and drafts a reply.

Run it on your own computer (Reddit blocks cloud servers):
    python3 outreach/radar/radar.py            # one check
    python3 outreach/radar/radar.py --loop 150 # check every 150 minutes

Standard library only. Settings live in config.json next to this file.
"""
import argparse, csv, datetime as dt, json, os, re, sys, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
SEEN = os.path.join(HERE, "seen.json")


def load_config():
    with open(os.path.join(HERE, "config.json"), encoding="utf-8") as f:
        return json.load(f)


# ---------- fetching ----------

def get_json(url, ua):
    req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fetch_reddit(cfg):
    """New posts from each subreddit, plus a keyword search across Reddit."""
    ua, posts = cfg["user_agent"], []
    urls = [f"https://www.reddit.com/r/{s}/new.json?limit=50&raw_json=1" for s in cfg["subreddits"]]
    for q in cfg["search_queries"]:
        urls.append("https://www.reddit.com/search.json?sort=new&t=day&limit=50&raw_json=1&q=" + urllib.parse.quote(q))
    for url in urls:
        try:
            data = get_json(url, ua)
        except Exception as e:  # one bad source should not stop the rest
            print(f"  skip {url.split('?')[0]}: {e}", file=sys.stderr)
            continue
        for c in data.get("data", {}).get("children", []):
            d = c.get("data", {})
            posts.append({
                "id": "reddit:" + d.get("id", ""),
                "source": "r/" + d.get("subreddit", ""),
                "title": d.get("title", ""),
                "body": d.get("selftext", ""),
                "flair": d.get("link_flair_text") or "",
                "author": d.get("author", ""),
                "url": "https://www.reddit.com" + d.get("permalink", ""),
                "created": d.get("created_utc", 0),
            })
        time.sleep(2)  # stay well under Reddit's rate limit
    return posts


# ---------- scoring ----------

def find_budget(text):
    m = re.search(r"\$\s?\d[\d,]*(?:\.\d+)?(?:\s?[-–to]+\s?\$?\s?\d[\d,]*)?(?:\s?(?:/|per)\s?(?:hr|hour|video|vid|clip|short|ep|episode|week|wk|month|mo))?", text, re.I)
    return m.group(0).strip() if m else ""


def score(post, cfg):
    """Returns (score, niche, reasons) or None when the post is not a hiring post for us."""
    t = f"{post['title']} {post['flair']}".lower()
    text = f"{t} {post['body'].lower()}"
    if any(re.search(p, t) for p in cfg["offer_patterns"]):  # editors advertising themselves
        return None
    if not any(re.search(p, text) for p in cfg["hiring_patterns"]):
        return None
    if any(re.search(p, text) for p in cfg["skip_patterns"]):
        return None
    s, reasons = 0, []
    niche = "short-form"
    for name, words in cfg["niches"].items():
        hits = [w for w in words if re.search(r"\b" + re.escape(w) + r"\b", text)]
        if hits:
            s += cfg["niche_weight"][name] * min(len(hits), 3)
            reasons.append(f"{name}: {', '.join(hits[:3])}")
            if cfg["niche_weight"][name] >= cfg["niche_weight"].get(niche, 0):
                niche = name
    budget = find_budget(post["title"] + " " + post["body"])
    if budget:
        s += 3
        reasons.append("budget " + budget)
    for w in cfg["red_flags"]:
        if re.search(r"\b" + re.escape(w) + r"\b", text):
            s -= 4
            reasons.append("red flag: " + w)
    return s, niche, budget, reasons


# ---------- drafting ----------

def draft(post, niche, budget, cfg):
    site, ig = cfg["portfolio"], cfg["instagram"]
    lead = {
        "comedy": "We're a small studio that only cuts comedy, podcasts and creator content. We let the laughs breathe so the timing lands like it did in the room, and captions stay on the beat without spoiling the punchline.",
        "podcast": "We're a small studio that cuts podcasts and comedy into captioned vertical clips: we find the moments that stand on their own, reframe to 9:16 and caption on the beat.",
        "short-form": "We're a small studio that edits short-form for creators: hooks in the first 2 seconds, captions on the beat, and pacing that keeps people watching.",
    }.get(niche, "")
    topic = re.sub(r"^\s*\[[^\]]*\]\s*", "", post["title"]).strip().rstrip(".")
    lines = [f"Hey! Saw your post ({topic[:80]}). This is exactly what we do. {lead}", "",
             f"Our work, including a full breakdown of a stand-up clip (hook, captions, sound, timing): {site} (IG: {ig})", ""]
    if budget:
        lines.append(f"Your budget ({budget}) works for us. Happy to start with one clip from your footage so you can judge the quality first.")
    else:
        lines.append("Happy to start with one clip from your footage so you can judge the quality before committing. Just send a link.")
    return "\n".join(lines)


# ---------- state, outputs ----------

def load_seen():
    try:
        with open(SEEN, encoding="utf-8") as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()


def save_seen(seen):
    with open(SEEN, "w", encoding="utf-8") as f:
        json.dump(sorted(seen)[-5000:], f)


def append_prospects(leads, path):
    if not path or not os.path.exists(path):
        return 0
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    header, known = rows[0], {r[-1] for r in rows[1:] if r} | {" ".join(r) for r in rows[1:]}
    col = {h: i for i, h in enumerate(header)}
    added = 0
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        for L in leads:
            if any(L["url"] in k for k in known):
                continue
            row = [""] * len(header)
            vals = {"name": f"Radar: {L['title'][:60]} (u/{L['author']})", "type": "reddit-hiring",
                    "tier": L["tier"], "fit": str(min(5, max(2, L["score"] // 3))),
                    "where_to_reach": L["url"], "status": f"radar-found {dt.date.today()}", "next_step": "send drafted reply",
                    "clip_gap": "; ".join(L["reasons"])[:120]}
            for k, v in vals.items():
                if k in col:
                    row[col[k]] = v
            w.writerow(row)
            added += 1
    return added


def notify(cfg, leads):
    topic = cfg.get("ntfy_topic", "").strip()
    if not topic or not leads:
        return
    body = "\n".join(f"{L['tier']} {L['title'][:70]}" for L in leads[:5]).encode("utf-8")
    req = urllib.request.Request("https://ntfy.sh/" + urllib.parse.quote(topic), data=body,
                                 headers={"Title": f"AVE radar: {len(leads)} new lead(s)", "Click": leads[0]["url"], "Tags": "movie_camera"})
    try:
        urllib.request.urlopen(req, timeout=20)
    except Exception as e:
        print("  notify failed:", e, file=sys.stderr)


def run(cfg, fixture=None, prospects=None):
    now = time.time()
    posts = json.load(open(fixture, encoding="utf-8")) if fixture else fetch_reddit(cfg)
    seen, leads = load_seen(), []
    for p in posts:
        if p["id"] in seen or now - p["created"] > cfg["max_age_hours"] * 3600:
            continue
        r = score(p, cfg)
        seen.add(p["id"])
        if not r or r[0] < cfg["min_score"]:
            continue
        s, niche, budget, reasons = r
        tier = "HOT" if s >= cfg["hot_score"] else "WARM"
        age = int((now - p["created"]) / 60)
        leads.append({**p, "score": s, "tier": tier, "niche": niche, "budget": budget, "reasons": reasons,
                      "age_min": age, "reply": draft(p, niche, budget, cfg)})
    save_seen(seen)
    leads.sort(key=lambda L: (-L["score"], L["age_min"]))
    if not leads:
        print(f"0 new leads ({len(posts)} posts checked)")
        return leads
    os.makedirs(OUT, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y-%m-%d-%H%M")
    path = os.path.join(OUT, f"{stamp}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# AVE lead radar, {stamp}\n\n{len(leads)} new lead(s) from {len(posts)} posts checked.\n\n")
        for i, L in enumerate(leads, 1):
            f.write(f"## {i}. {L['tier']} · {L['title']}\n{L['url']}\n\n"
                    f"{L['source']} · u/{L['author']} · posted {L['age_min']} min ago · score {L['score']}"
                    f"{' · ' + L['budget'] if L['budget'] else ''}\nWhy: {'; '.join(L['reasons'])}\n\n"
                    "Open the post first; skip it if it says filled.\n\n"
                    + "\n".join("> " + x if x else ">" for x in L["reply"].split("\n")) + "\n\n")
    added = append_prospects(leads, prospects)
    notify(cfg, leads)
    print(f"{len(leads)} new lead(s) -> {os.path.relpath(path)}" + (f" ({added} added to prospects.csv)" if prospects else ""))
    return leads


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--loop", type=int, metavar="MIN", help="keep running, checking every MIN minutes")
    ap.add_argument("--fixture", help="read posts from a JSON file instead of Reddit (for testing)")
    ap.add_argument("--prospects", default=os.path.join(HERE, "..", "prospects.csv"),
                    help="tracker to append new leads to (default: outreach/prospects.csv; skipped if missing)")
    a = ap.parse_args()
    cfg = load_config()
    while True:
        run(cfg, a.fixture, a.prospects)
        if not a.loop:
            break
        time.sleep(a.loop * 60)


if __name__ == "__main__":
    main()
