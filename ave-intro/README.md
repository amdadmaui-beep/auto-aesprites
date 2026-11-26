# AVE Studio intro

`AVE_Studio_Intro_16x9.mp4`: 1920x1080, 60 fps, 20.6 s. A remake of a reference motion-designer intro, beat for
beat, with AVE Studio's name, an inflated 3D AVE logo, and our own work in place of the reference's
"my work was deleted, I forgot to backup" gag. The audio is the reference's music track.

| Time | Scene |
|---|---|
| 0.0-2.9 | "Hi" -> pill "We're AVE Studio." + "Motion Studio." over inflated lime AVE letters and stickers |
| 3.0-5.4 | "What do we usually make?" with the colour-cycling "make", then a pixel dissolve |
| 5.5-9.5 | Prompt box: "We can.. ummm" -> "Yes we can make motion", stickers, cat, "I like cats / WE DO" |
| 9.6-12.0 | Our work card (More Heat reel): "Our work. Backed up, obviously." |
| 12.0-14.9 | Work stack: AVE Studio promo, Cursor spot, Notion spot, dropping in like the reference's pages |
| 16.8-19.5 | "See you later." |

Rebuild (from `film/`):
```bash
bash ../tools/clips.sh                 # work-clip frame sequences -> clips/
python ../tools/blob.py                # inflated AVE letters -> img/blob_*.png
node render.mjs --video=build/video.mp4 --sub=2
ffmpeg -i <reference>.mp4 -vn -ar 48000 -ac 2 build/audio.wav
ffmpeg -i build/video.mp4 -i build/audio.wav -c:v copy -c:a aac -b:a 320k -shortest ../AVE_Studio_Intro_16x9.mp4
```
Frame-by-frame study of the reference was done with the `reanimate` skill (`.claude/skills/reanimate`).
