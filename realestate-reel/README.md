# Real estate "Before / After" reel

This rebuilds the client's reference reel with new footage. It keeps the reference's format, its 26 cut points and its audio. The output is 1080×1920 at 30 fps, 28.8 s long.

- **Layout:** a white page, with "Before" (a still photo card) on top and "After" (the moving video edit) below. It matches the reference's 720×1280 layout scaled ×1.5, with rounded cards and soft shadows.
- **"Before"** is a still frame of the same clip, given a flat camera-original look: duller, a touch dark and cool.
- **"After"** is the same space as a graded, moving edit.
- **Moves taken from the reference:**
  - a white-flash opener;
  - lights switching on (1.07–1.63 s);
  - a real sunset-to-dusk timelapse;
  - a box reveal from the aerial into the pool (12.63 s);
  - detail close-ups popping in on the beat (15.9–16.8 s and 27.4–28.9 s);
  - a circle reveal into the kitchen (24.57 s).

## Footage

All footage is from Mixkit, under the Mixkit License: free for commercial use, no attribution required. The clips are referenced by their Mixkit id; download them from `https://assets.mixkit.co/videos/<id>/<id>-1080.mp4` (or `-720`).

| id | clip |
|---|---|
| 4047 | boutique hotel room and terrace |
| 3111 | master bedroom and window |
| 3109 | minimalist room with a couple of beds |
| 4205 | sun setting over a garden |
| 8603 | aerial view of a manor house in a hilly orchard |
| 47286 | backyard of a large villa with a garden and a pool |
| 3110 | minimalist room with gray sofa |
| 43033 | interior view of a spacious modern kitchen |
| 4488 | hotel room with modern minimalist style |
| 4029 | interior of a room with terrace |
| 4046 | white luxury boutique hotel room |
| 6773 | swimming pool in a resort garden |
| 9902 | luxury vacation resort complex with pool by the sea |
| 4045 | luxury swimming pool |
| 40109 | water texture of a swimming pool |
| 3090 | modern living room with wooden furniture |
| 4196 | luxury hotel room panning shot |
| 4641 | indoor pool with a great view |
| 3112 | interior of a department room |

The audio is the reference reel's soundtrack, supplied by the client. It is not committed: clear its license before publishing.

## Build
```bash
python build_reel.py <clips_dir> <reference_audio.wav> build/RealEstate_BeforeAfter_9x16.mp4   # numpy + Pillow + ffmpeg
```

To use real client work instead of stock, swap each `SEG` entry's clip for that client's own raw photo ("Before") and finished video ("After").

## V2 (`build_reel2.py`): 4K
- **Resolution:** 2160×3840 at 30 fps, 31.1 s (28.9 s reel plus a 2.2 s outro).
- **Transitions from the reference:**
  - **diagonal glass shards:** dusk to the manor aerial at 4.53 s, and kitchen to villa at 25.40 s;
  - **vertical panel builds:** terrace to the white suite at 9.55 s, and aerial to the pool at 12.55 s;
  - the box reveal (at 21.20 s) and circle reveal (at 24.57 s) are kept.
- **Designed backdrop:**
  - an ambient wash of the current "After" shot, blurred and pulled toward cream;
  - a faint architectural grid with corner ticks around each card;
  - "Before" and "After" chips;
  - a small AVE Studio header.
- **Outro:** the AVE logo builds from the same vertical panels, then "STUDIO" and a tagline appear. The sound is bloops plus a ding from `sfx_library/satisfying/`.

```bash
python build_reel2.py <clips_dir> <reference_audio.wav> ../sfx_library build/RealEstate_BeforeAfter_V2_4K.mp4
```
