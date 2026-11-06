#!/usr/bin/env python3
"""AVE Clip-finder: find the best short-form moments in a long stand-up set or podcast.

  python3 clipfinder.py <video file | Google Drive link | YouTube link> [--n 5] [--min 20] [--max 60] [--out DIR]

What it does
  1. Transcribes the audio locally (faster-whisper, free, no API).
  2. Measures the room: loudness between words = laughs and reactions.
  3. Scores every 20–60 s stretch that starts and ends on a full sentence:
       hook (first 2 s), payoff (laugh right after it ends), laughs inside, energy,
       stands on its own, quotable line.
  4. Picks the top N that don't overlap, cuts each to 9:16 with captions
     (AVE default look: bold white sentence case, one lime key word), and writes
     report.html + report.md with the score breakdown and a "why this moment" note.

YouTube links only work on a home connection (YouTube blocks cloud servers).
Needs: ffmpeg, python packages faster-whisper (and yt-dlp for YouTube).
"""
import argparse, json, math, os, re, subprocess, sys, html, wave, array, shutil, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, 'fonts')
LIME = '&H002EFFC8'  # ASS colour is &HAABBGGRR: lime #C8FF2E
WHITE = '&H00FFFFFF'

def sh(cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw).stdout

# ---------- 1. get the video ----------
def fetch(src, work):
    if os.path.exists(src):
        return os.path.abspath(src)
    os.makedirs(work, exist_ok=True)
    m = re.search(r'(?:/d/|id=)([\w-]{20,})', src) or (re.fullmatch(r'[\w-]{25,}', src) and re.match(r'(.*)', src))
    if 'drive.google' in src or re.fullmatch(r'[\w-]{25,}', src):
        fid = m.group(1)
        out = os.path.join(work, f'drive_{fid}.mp4')
        if not os.path.exists(out):
            print('Downloading from Google Drive…')
            urllib.request.urlretrieve(f'https://drive.usercontent.google.com/download?id={fid}&export=download&confirm=t', out)
        return out
    if 'youtu' in src:
        out = os.path.join(work, 'youtube.mp4')
        print('Downloading from YouTube…')
        subprocess.run(['yt-dlp', '-f', 'bv*[height<=1080]+ba/b', '--merge-output-format', 'mp4', '-o', out, src], check=True)
        return out
    sys.exit(f'Can\'t find or download: {src}')

# ---------- 2. transcribe ----------
def transcribe(video, work, model_size):
    cache = os.path.join(work, 'transcript.json')
    if os.path.exists(cache):
        return json.load(open(cache))
    wav = os.path.join(work, 'audio.wav')
    sh(['ffmpeg', '-v', 'error', '-y', '-i', video, '-ac', '1', '-ar', '16000', wav])
    from faster_whisper import WhisperModel
    print(f'Transcribing with the {model_size} model (free, runs here)…')
    model = WhisperModel(model_size, device='cpu', compute_type='int8')
    import numpy as np
    w = wave.open(wav); audio = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    segs, info = model.transcribe(audio, word_timestamps=True, vad_filter=False, beam_size=1)
    words = []
    for s in segs:
        for w in s.words or []:
            words.append({'w': w.word.strip(), 's': round(w.start, 3), 'e': round(w.end, 3)})
        print(f'  {s.end/60:5.1f} min', end='\r')
    json.dump(words, open(cache, 'w'))
    return words

def loudness(work, step=0.1):
    """RMS loudness every `step` seconds, as a list of floats."""
    w = wave.open(os.path.join(work, 'audio.wav'))
    n = int(w.getframerate() * step)
    data = array.array('h', w.readframes(w.getnframes()))
    out = []
    for i in range(0, len(data), n):
        c = data[i:i + n]
        out.append(math.sqrt(sum(x * x for x in c) / max(1, len(c))) if c else 0)
    return out

# ---------- 3. score ----------
SWEAR = re.compile(r"f\*?u?ck|sh\*?it|bitch|ass\b|damn|hell\b|dick|crap", re.I)
HOOKWORDS = re.compile(r"^(so|my|i|you|never|nobody|the worst|have you|what|why|how|this|here's|listen|okay so)\b", re.I)
VAGUE_START = re.compile(r"^(and|but|or|because|which|so then|then|that's why|he|she|it|they|this one)\b", re.I)

def sentences(words):
    out, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        gap = words[i + 1]['s'] - w['e'] if i + 1 < len(words) else 9
        if re.search(r'[.!?]$', w['w']) or gap > 1.1:
            out.append(cur); cur = []
    if cur: out.append(cur)
    return [{'s': c[0]['s'], 'e': c[-1]['e'], 'text': ' '.join(x['w'] for x in c), 'words': c} for c in out]

def laughs(words, rms, step=0.1):
    """Stretches with no words but a loud room (laughs, applause, reactions)."""
    med = sorted(rms)[len(rms) // 2] or 1
    spoken = [False] * len(rms)
    for w in words:
        for k in range(int(w['s'] / step), min(len(rms), int(w['e'] / step) + 1)): spoken[k] = True
    events, k = [], 0
    while k < len(rms):
        if not spoken[k] and rms[k] > med * 1.35:
            j = k
            while j < len(rms) and not spoken[j] and rms[j] > med * 1.1: j += 1
            if (j - k) * step >= 0.6:
                events.append({'s': k * step, 'e': j * step, 'strength': sum(rms[k:j]) / (j - k) / med})
            k = j
        k += 1
    return events

def score_window(sents, a, b, laugh_ev, rms, step=0.1):
    S = sents[a:b + 1]; start, end = S[0]['s'], S[-1]['e']; dur = end - start
    text = ' '.join(x['text'] for x in S)
    first2 = ' '.join(w['w'] for x in S for w in x['words'] if w['s'] < start + 2.2)
    inside = [l for l in laugh_ev if start <= l['s'] <= end]
    after = [l for l in laugh_ev if end - 0.5 <= l['s'] <= end + 3.5]
    seg = rms[int(start / step):int(end / step)] or [0]
    med = sorted(rms)[len(rms) // 2] or 1
    energy = min(1, (sum(seg) / len(seg)) / med / 2)
    hook = 0.35 * bool(HOOKWORDS.search(first2.strip())) + 0.25 * ('?' in first2) + 0.2 * bool(re.search(r'\d', first2)) + 0.2 * (len(S[0]['words']) <= 12)
    payoff = min(1, sum(l['strength'] for l in after) / 3)
    lots = min(1, len(inside) / max(1, dur / 15))
    alone = 1 - 0.6 * bool(VAGUE_START.search(S[0]['text'])) - 0.2 * (dur < 22)
    quot = min(1, 0.4 * bool(SWEAR.search(text)) + 0.3 * bool(re.search(r'\d', text)) + 0.3 * any(len(x['words']) <= 7 and x['text'].endswith(('!', '?', '.')) for x in S[-2:]))
    parts = {'hook': hook, 'payoff': payoff, 'laughs': lots, 'energy': energy, 'stands alone': max(0, alone), 'quotable': quot}
    W = {'hook': 22, 'payoff': 28, 'laughs': 18, 'energy': 10, 'stands alone': 14, 'quotable': 8}
    total = sum(parts[k] * W[k] for k in W) + 6 * max(0, 1 - abs(dur - 38) / 30)  # research: 30–45 s performs best
    return {'s': start, 'e': end, 'dur': dur, 'text': text, 'score': round(total), 'parts': {k: round(v, 2) for k, v in parts.items()}, 'laughs_inside': len(inside), 'laugh_after': bool(after), 'a': a, 'b': b}

def why(c):
    p, bits = c['parts'], []
    if p['payoff'] > .4: bits.append('the room laughs right as it ends, so it lands on a punchline')
    if c['laughs_inside'] >= 2: bits.append(f"{c['laughs_inside']} laughs inside it")
    if p['hook'] >= .5: bits.append('opens with a strong first line')
    if p['stands alone'] >= .9: bits.append('makes sense without the rest of the set')
    if p['quotable'] >= .5: bits.append('has a quotable line')
    if p['energy'] > .6: bits.append('high energy delivery')
    return (bits[0][0].upper() + bits[0][1:] + (', ' + ', '.join(bits[1:]) if len(bits) > 1 else '') + '.') if bits else 'Best of what’s left: solid but no big laugh.'

def find(words, rms, n, lo, hi):
    sents, ev = sentences(words), laughs(words, rms)
    cands = []
    for a in range(len(sents)):
        for b in range(a, len(sents)):
            d = sents[b]['e'] - sents[a]['s']
            if d > hi: break
            if d >= lo: cands.append(score_window(sents, a, b, ev, rms))
    cands.sort(key=lambda c: -c['score'])
    picked = []
    for c in cands:
        if all(c['e'] <= p['s'] or c['s'] >= p['e'] for p in picked): picked.append(c)
        if len(picked) == n: break
    for c in picked: c['why'] = why(c)
    return picked, ev, sents

# ---------- 4. cut + captions ----------
def ass_time(t):
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f'{h}:{m:02d}:{s:05.2f}'

def key_index(chunk):
    """The word to light up: a number, a swear, or the longest word."""
    for i, w in enumerate(chunk):
        if re.search(r'\d', w['w']) or SWEAR.search(w['w']): return i
    return max(range(len(chunk)), key=lambda i: len(re.sub(r'\W', '', chunk[i]['w'])))

def captions(clip, words, path, W, H):
    ws = [w for w in words if clip['s'] - 0.05 <= w['s'] < clip['e']]
    chunks, cur = [], []
    for w in ws:
        cur.append(w)
        if len(cur) >= 4 or re.search(r'[.!?,]$', w['w']): chunks.append(cur); cur = []
    if cur: chunks.append(cur)
    fs = int(W * 0.078)
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: AVE,Inter,{fs},{WHITE},{WHITE},&H96000000,&H96000000,-1,0,0,0,100,100,0,0,1,0,3,2,{int(W*.08)},{int(W*.08)},{int(H*.3)},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    for i, c in enumerate(chunks):
        s = c[0]['s'] - clip['s']; e = (chunks[i + 1][0]['s'] if i + 1 < len(chunks) else c[-1]['e'] + 0.4) - clip['s']
        k = key_index(c) if len(c) > 1 else -1
        txt = ' '.join((r'{\c' + LIME + '}' + w['w'] + r'{\c' + WHITE + '}') if j == k else w['w'] for j, w in enumerate(c))
        lines.append(f'Dialogue: 0,{ass_time(max(0, s))},{ass_time(max(s + .3, e))},AVE,,0,0,0,,{{\\fad(60,40)\\t(0,120,\\fscx104\\fscy104)\\t(120,220,\\fscx100\\fscy100)}}{txt}')
    open(path, 'w').write(head + '\n'.join(lines) + '\n')

def cut(video, clip, words, outdir, idx):
    probe = json.loads(sh(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'json', video]))['streams'][0]
    w, h = probe['width'], probe['height']
    W, H = 1080, 1920
    vf = f'scale={W}:{H}' if h >= w * 1.6 else f'crop=ih*9/16:ih,scale={W}:{H}'  # vertical stays; wide gets a centre crop
    ass = os.path.join(outdir, f'clip{idx}.ass'); captions(clip, words, ass, W, H)
    out = os.path.join(outdir, f'clip{idx}_{clip["score"]}.mp4')
    sh(['ffmpeg', '-v', 'error', '-y', '-ss', f'{max(0, clip["s"] - 0.15):.2f}', '-t', f'{clip["dur"] + 0.6:.2f}', '-i', video,
        '-vf', f"{vf},ass={ass}:fontsdir={FONTS}", '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '21', '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', out])
    thumb = out.replace('.mp4', '.jpg'); sh(['ffmpeg', '-v', 'error', '-y', '-ss', '1.5', '-i', out, '-frames:v', '1', '-vf', 'scale=360:-2', thumb])
    return out, thumb

def mmss(t): return f'{int(t // 60)}:{int(t % 60):02d}'

def report(src, picked, outdir, files):
    md = [f'# Clip-finder report\n\nSource: `{src}`\n']
    cards = []
    for i, (c, (mp4, jpg)) in enumerate(zip(picked, files), 1):
        bars = ''.join(f'<div class=b><span>{k}</span><i style="width:{v*100:.0f}%"></i></div>' for k, v in c['parts'].items())
        md.append(f"## {i}. Score {c['score']} · {mmss(c['s'])}–{mmss(c['e'])} ({c['dur']:.0f}s)\n\n**Why:** {c['why']}\n\n> {c['text']}\n\nFile: `{os.path.basename(mp4)}`\n")
        cards.append(f"<div class=c><video src='{os.path.basename(mp4)}' poster='{os.path.basename(jpg)}' controls playsinline preload=none></video><div><h2>{i}. <b>{c['score']}</b> <small>{mmss(c['s'])}–{mmss(c['e'])} · {c['dur']:.0f}s</small></h2><p class=w>{html.escape(c['why'])}</p>{bars}<p class=t>{html.escape(c['text'])}</p></div></div>")
    open(os.path.join(outdir, 'report.md'), 'w').write('\n'.join(md))
    open(os.path.join(outdir, 'report.html'), 'w').write(f"""<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>Clip-finder report</title>
<style>body{{margin:0;background:#0E0E0E;color:#F3F2EE;font:15px/1.5 system-ui,sans-serif;padding:24px 16px}}h1{{font-size:28px;margin:0 0 4px}}.src{{color:#9C9990;margin:0 0 24px;word-break:break-all}}
.c{{display:grid;grid-template-columns:220px 1fr;gap:20px;background:#171716;border-radius:16px;padding:16px;margin-bottom:16px}}video{{width:100%;border-radius:10px;background:#000}}
h2{{margin:0 0 6px;font-size:18px}}h2 b{{color:#C8FF2E;font-size:26px}}small{{color:#9C9990;font-weight:400}}.w{{margin:0 0 10px}}.t{{color:#9C9990;font-size:14px}}
.b{{display:grid;grid-template-columns:110px 1fr;align-items:center;gap:8px;font-size:12.5px;color:#9C9990;margin:3px 0}}.b i{{display:block;height:6px;border-radius:3px;background:#C8FF2E}}
@media(max-width:640px){{.c{{grid-template-columns:1fr}}video{{max-width:260px}}}}</style>
<h1>Clip-finder: top {len(picked)} moments</h1><p class=src>{html.escape(src)}</p>{''.join(cards)}""")

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('src'); ap.add_argument('--n', type=int, default=5); ap.add_argument('--min', type=float, default=20); ap.add_argument('--max', type=float, default=60)
    ap.add_argument('--out', default='clipfinder-out'); ap.add_argument('--model', default='small.en', help='tiny.en, base.en, small.en (default), medium.en')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True); work = os.path.join(a.out, '_work')
    video = fetch(a.src, work); os.makedirs(work, exist_ok=True)
    words = transcribe(video, work, a.model); rms = loudness(work)
    picked, ev, sents = find(words, rms, a.n, a.min, a.max)
    print(f'\n{len(words)} words, {len(sents)} sentences, {len(ev)} laughs/reactions found. Cutting {len(picked)} clips…')
    files = [cut(video, c, words, a.out, i) for i, c in enumerate(picked, 1)]
    report(a.src, picked, a.out, files)
    json.dump({'picked': picked, 'laughs': ev}, open(os.path.join(a.out, 'clips.json'), 'w'), indent=1)
    for i, c in enumerate(picked, 1): print(f"{i}. {c['score']:3d}  {mmss(c['s'])}–{mmss(c['e'])}  {c['why']}")
    print(f'\nDone. Open {os.path.join(a.out, "report.html")}')

if __name__ == '__main__':
    main()
