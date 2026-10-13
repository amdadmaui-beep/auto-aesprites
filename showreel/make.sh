#!/usr/bin/env bash
# Full pipeline: score -> beats -> frames -> loudness-normalized mux.
set -euo pipefail
cd "$(dirname "$0")"
python3 synth.py
node render.mjs
# two-pass loudnorm to -14 LUFS integrated, -1 dBTP
M=$(ffmpeg -hide_banner -i build/score_raw.wav -af loudnorm=I=-14:TP=-1:LRA=11:print_format=json -f null - 2>&1 | sed -n '/{/,/}/p')
get() { echo "$M" | grep "\"$1\"" | sed 's/.*: "\(.*\)".*/\1/'; }
ffmpeg -y -hide_banner -loglevel error -i build/score_raw.wav -af "loudnorm=I=-14:TP=-1:LRA=11:measured_I=$(get input_i):measured_TP=$(get input_tp):measured_LRA=$(get input_lra):measured_thresh=$(get input_thresh):offset=$(get target_offset):linear=true,aresample=48000" build/score.wav
ffmpeg -y -hide_banner -loglevel error -framerate 60 -i build/frames/f_%05d.png -i build/score.wav \
  -c:v libx264 -preset slow -pix_fmt yuv420p -crf 16 -movflags +faststart -c:a aac -b:a 320k -shortest reel.mp4
ffmpeg -hide_banner -i reel.mp4 -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I|Peak):"
