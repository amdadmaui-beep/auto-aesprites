# AVE Clip-finder

Finds the best short-form moments in a long stand-up set or podcast and cuts them to 9:16 with captions. Free: runs on your machine, no AI service bills.

```bash
pip install faster-whisper yt-dlp
python3 clipfinder.py "<video file | Google Drive link | YouTube link>" --n 5 --out my-clips
```

Open `my-clips/report.html`: every clip with its score, a “why this moment” note and the transcript.

**How it scores** each 20–60 s stretch that starts and ends on a full sentence:
payoff (the room laughs right as it ends) 28 · hook in the first 2 s 22 · laughs inside 18 · stands on its own 14 · energy 10 ·
quotable line 8 · up to +6 for 30–45 s (what the research says performs best; see `outreach/research/REPORT.md`).
Laughs are found by listening for a loud room between words, so it works best on live sets with a crowd.

**Options:** `--n` clips (5), `--min`/`--max` seconds (20/60), `--model` tiny.en / base.en / small.en (default, good) / medium.en (best, slow).
Captions use the AVE default look (bold white sentence case, one lime key word). Client looks like Jackie’s stay reserved for their clips.

**Notes:** YouTube blocks cloud servers, so YouTube links work on your laptop, not in a cloud session. About 3–4 minutes per 13 minutes of audio on a 4-core machine.
