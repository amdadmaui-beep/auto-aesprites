# AVE lead radar

Finds fresh "looking for an editor" posts (comedy, podcast, short-form) within hours of posting, scores them against the playbook, and drafts a reply in AVE's voice. You read the post and send the reply yourself.

Why: on hiring posts the first few replies win. Our 16 earlier hiring-post replies (Oct 30 to Nov 3) got no answers, most likely because the posts were days old.

## Run it (on your own computer; Reddit blocks cloud servers)

Needs Python 3 (no extra packages).

```bash
python3 outreach/radar/radar.py
```

```bash
python3 outreach/radar/radar.py --loop 150
```

The first checks once; the second keeps running and checks every 150 minutes. On Windows use `py` instead of `python3`.

Each run writes a report to `outreach/radar/out/<date-time>.md` (newest leads first, with the drafted reply) and adds new leads to `outreach/prospects.csv` as `radar-found`. Posts it has already seen are remembered in `seen.json`, so nothing shows up twice.

## Get a phone alert (free)

1. Install the free **ntfy** app (iPhone or Android).
2. In the app, subscribe to a topic with a long random name nobody would guess, like `ave-radar-k3x9q2m7`.
3. Put the same name in `config.json` as `"ntfy_topic": "ave-radar-k3x9q2m7"`.

Every run with new leads now pings your phone; tapping it opens the top post.

## What it checks

`config.json` holds the subreddits, search phrases, what counts as hiring, what to skip (filled, unpaid, rev share, editors advertising themselves) and how leads are scored (comedy > podcast > other short-form, a posted budget counts extra). Edit it freely.

## Sending replies

- Open the post first and skip it if it's filled.
- Change the first line to mention one real detail from their post.
- Send from your Reddit account, then set the lead's status in `prospects.csv` to `messaged`.
- Answers to "how much?", "can we call?" and the rest are in `outreach/PLAYBOOK.md`.
