#!/usr/bin/env bash
# Extracts the work-showcase frame sequences used by film/index.html (run from ave-intro/film).
set -e
A=../..
ext(){ mkdir -p clips/$1; ffmpeg -v error -y -ss $2 -t $3 -i $4 -vf "fps=30,scale=$5:-2" -q:v 3 clips/$1/%03d.jpg; }
ext heat 3.0 2.6 $A/ave-promo/AVE_More_Heat_Reel_V10.mp4 540
ext notion 18.6 3.2 $A/notion-spec/Notion_Agents_Spec_V3_16x9.mp4 960
ext cursor 14 3.2 $A/cursor-spec/film6/build/Cursor_Spec_AVE_V6_16x9_SFXonly.mp4 960
ext cat 1.0 3.2 $A/ave-promo/AVE_Studio_Promo_V3.mp4 960
