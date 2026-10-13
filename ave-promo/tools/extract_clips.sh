#!/usr/bin/env bash
# Rebuild film/clips/ (JPEG frame sequences + audio) from the AVE Studio Showcase Drive folder.
# Needs: curl, ffmpeg, python3 with opencv-python-headless + numpy (for the label clean-up step).
set -euo pipefail
HERE=$(cd "$(dirname "$0")/.." && pwd); SRC=$HERE/footage; F=$HERE/film/clips; mkdir -p "$SRC" "$F/audio"
dl(){ [ -f "$SRC/$2.mp4" ] || curl -sL -o "$SRC/$2.mp4" "https://drive.usercontent.google.com/download?id=$1&export=download&confirm=t"; }
dl 1e4-KzvEm9eGEfjefBrdtjAlfsFHKzsx0 podcast_ave
dl 1b5yVTG7RUkUEMQA5tro5srHXTivf2zLa podcast_mindpump
dl 13NZkCYCF1iLFeeZ2VZDcKOt62jON568h comedy_killtony_dustin
dl 1XEKnqG1UIZsoweBMuMqLnF9qk2mf-LIf comedy_jackie_safe
dl 1Rw7L79Ev0p_yphcUnv_75vwtOGX80PM3 comedy_conor
dl 19vb41KDZf9d8gzPPJHNSiE12U2jqyasv comedy_spitballers
dl 1C4pebJZi9tNBdNftt_alB_25RRjo-Qqj motion_notion
ex(){ mkdir -p "$F/$1"; ffmpeg -v error -y -ss "$3" -t "$4" -i "$SRC/$2.mp4" -vf "fps=30,$5" -q:v 4 "$F/$1/%04d.jpg"; }
ex card_comedy comedy_jackie_safe 40.0 4.0 "scale=360:640"
ex card_podcast comedy_spitballers 0.0 4.0 "scale=360:640"
ex card_motion motion_notion 19.5 4.0 "scale=640:360"
ex longform podcast_mindpump 9.0 4.6 "crop=636:354:222:1236"
ex mp_raw podcast_mindpump 1.3 7.4 "crop=636:354:222:1236"
ex mp_edit podcast_mindpump 1.3 7.4 "crop=960:900:60:250,scale=720:675"
ex feed_jackie comedy_jackie_safe 10.0 4.2 "scale=360:640"
ex feed_kt comedy_killtony_dustin 45.0 4.2 "scale=360:640"
ex feed_sp comedy_spitballers 3.0 4.2 "scale=360:640"
ex feed_conor comedy_conor 17.0 4.2 "scale=360:640"
ex flash_kt comedy_killtony_dustin 24.9 1.9 "scale=540:960"
ex flash_sp comedy_spitballers 9.9 1.9 "scale=540:960"
ex hero_motion motion_notion 34.0 4.6 "scale=1152:648"
for s in "kt comedy_killtony_dustin 24.9 1.9" "sp comedy_spitballers 9.9 1.9" "hero motion_notion 34.0 4.6"; do
  set -- $s; ffmpeg -v error -y -ss "$3" -t "$4" -i "$SRC/$2.mp4" -vn -ac 2 -ar 48000 "$F/audio/$1.wav"; done
# paint out labels baked into the sample layout (the film shows its own labels + CC BY credit)
python3 - "$F" <<'PY'
import cv2, numpy as np, glob, sys
F=sys.argv[1]+'/'
m=np.zeros((354,636),np.uint8); cv2.rectangle(m,(205,0),(432,24),255,-1); cv2.rectangle(m,(276,322),(636,354),255,-1)
for d in ['mp_raw','longform']:
    for f in glob.glob(F+d+'/*.jpg'): cv2.imwrite(f,cv2.inpaint(cv2.imread(f),m,7,cv2.INPAINT_TELEA),[cv2.IMWRITE_JPEG_QUALITY,92])
m=np.zeros((675,720),np.uint8); cv2.rectangle(m,(262,0),(458,30),255,-1)
for f in glob.glob(F+'mp_edit/*.jpg'): cv2.imwrite(f,cv2.inpaint(cv2.imread(f),m,7,cv2.INPAINT_TELEA),[cv2.IMWRITE_JPEG_QUALITY,92])
PY
echo "clips ready in $F"
