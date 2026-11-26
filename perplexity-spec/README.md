# Perplexity spec spot (AVE Studio)

`Perplexity_Spec_AVE_4x3.mp4`: 1440x1080 (4:3, like the reference), 60 fps, 44.5 s. A beat-for-beat remake of a
reference AI-assistant ad, rebuilt for Perplexity entirely from UI (no footage), framed in an AVE Studio presentation
with Intro / Problem / Use Case / Call to Action tabs.

| Time | Tab | Beat |
|---|---|---|
| 0-2.7 | Intro | Phone rises, the Perplexity wordmark wipes in, 3D objects burst out |
| 2.7-9.7 | Problem | "Every day, there's something you've never done before." Words scatter into task icons, "Something new.", "Something exciting to figure out." |
| 9.7-14 | Problem | "You just want the answer, right?" A ring of tabs, threads, videos and ads; "S im pl e" pulled apart |
| 14-22.7 | Use Case | Dot to mark to wordmark; monitor rises, camera flies into Perplexity; "How do I make pizza at home?" typed and sent |
| 22.7-27 | Use Case | Landscape phone: sources, ingredients and steps tick off with the voice while the pizza builds |
| 27-31.9 | Use Case | "Perplexity can guide you."; "New [headphones / watch / speaker] product" |
| 31.9-38.5 | Use Case | Portrait phone walks through a watch setup; everyday tasks float out around it |
| 38.5-44.5 | Call to Action | "Learn it / Do it / Make it done"; mark draws, wordmark, "Start free today" |

Voice: Fish Audio `drama-3`, voice "Sarah", one main take plus one short pickup (speaker similarity 0.89), cut into
phrases and placed where the reference narrator speaks (`vo/assemble.py`). Music and sound design are original
(`film/audio.py`, 112 BPM, drop on "That's where Perplexity comes in"). Logo: official Perplexity SVG (Wikimedia Commons).

Rebuild (from `film/`):
```bash
python audio.py
ffmpeg -i build/mix_raw.wav -af "alimiter=limit=0.89:attack=2:release=60,loudnorm=I=-14:TP=-1:LRA=9" -ar 48000 build/mix.wav
node render.mjs --video=build/video.mp4 --sub=2
ffmpeg -i build/video.mp4 -i build/mix.wav -c:v copy -c:a aac -b:a 320k -shortest ../Perplexity_Spec_AVE_4x3.mp4
```
