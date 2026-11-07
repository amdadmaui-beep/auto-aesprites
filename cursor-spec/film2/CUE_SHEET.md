# Cursor V2: beat sheet and sound cue sheet

40.0 s · 1920×1080 · 60 fps · 120 BPM (one beat = 0.5 s). All times are in seconds and come from `cues.js`, which both the picture (`shots.js`) and the sound (`audio.py`) read.

**Sound palette ("creamy"):** round low-mid bodies with soft transients, and almost no energy above about 4 kHz. Broadband hiss is what read as "ripping paper" in V1, so it is gone. Measured on the SFX stem: 0.11% of the energy is above 5 kHz. Every sound is synthesised in `audio.py`; nothing is sampled.

| Kit sound | What it is |
| --- | --- |
| `thock` | A deep, lubed mechanical key: a round 165 Hz body, a hollow housing tone, a soft clack and a muffled bottom-out. |
| `plop` | A creamy bubble pop: a fast upward pitch glide with a round decay. |
| `boop` | A buttery downward UI pop. |
| `mag` | A magnetic snap: a sub thump, a mid knock and a whisper of a tick. |
| `whoosh` | Tight, rounded air capped at 3.2 kHz, with a tonal glide underneath. |
| `suck` | A reverse suction that swells and stops dead on the cut. |
| `impact` | A clean sub hit with a chest thump. No distortion is used anywhere. |
| `bell`, `tick`, `glide`, `swipe`, `roll` | Chimes, wooden ticks, tonal rises, selection swipes and number-roll ticks. |

**Mix:** the SFX bus sits about 3–17 dB above the music. The music ducks under every kick, which gives the score its pulse. A clean look-ahead limiter catches the impacts (a gain curve only, with no waveshaping). Delivery loudness is −14 LUFS and −1 dBTP.

## Beat sheet

| # | Time | Shot | Picture | Sound |
| --- | --- | --- | --- | --- |
| 1 | 0.00 | SH1 | Macro of the editor; ⌘ and K keycaps rise and press. | An 8th-note heartbeat kick that grows. The keycaps plop up, then two deep thocks for ⌘K. |
| 2 | 0.55 | SH2 | Code fragments fly in from 3D and lock line by line; the camera rushes through. | A whoosh, then 8 magnetic snaps panned across the lines. A suction into the cut. |
| 3 | 1.25 | SH3 | **IDEAS.** smash. | A music silence (1.17–1.25), then the big impact and a thock. |
| 4 | 1.75 | SH4 | **INTO REALITY.** | An impact plus a mag snap. The groove kick starts and a riser builds. |
| 5 | 2.55–3.0 | SH4 | Everything is pulled into the dark. | A reverse suction that cuts dead at 3.0. |
| 6 | 3.00 | SH5 | Official cube reveal; logo accent at 3.5; sheen at 3.7. | A low impact and a swell pad. A bell chord and sub for the accent. A tonal glide for the sheen. |
| 7 | 4.50 | SH6 | The camera orbits as the editor panels snap around the cube (5.3, 5.5, 5.7, 5.9); the icon lands at 6.05. | Half-time kick. 4 magnetic snaps with creamy plops, panned L/R. Plop and bell on the icon. |
| 8 | 6.25 | SH7 | **MEET CURSOR.** at 6.5. | A whoosh in, then an impact. The full groove arrives. |
| 9 | 8.00 | SH8 | Caret macro typing `useMetrics`. | 49 deep thocks in a groove with plucked arpeggios. |
| 10 | 8.90 | SH9 | A grey ghost suggestion appears. | A soft rising glide and a plop. |
| 11 | 10.00 | SH10 | Split screen: Tab keycap and code. Tab pressed at 10.3. | A music silence (10.18–10.3), then THE Tab: thock, mag, plop, sub and bell. The groove drops at full, with 16th hats. |
| 12 | 10.75 | SH11 | Accepted lines lift into 3D slabs, snap home at 11.55, and are selected at 12.05. | 6 ascending plops, then 6 snaps home. A creamy selection swipe and a tick. |
| 13 | 12.50 | SH12 | **LESS TYPING.** is typed; **MORE BUILDING.** letters snap up at 13.4. | Thocks for the typing. 14 buttery boops rising in pitch, then a mag. A snare fill into the next section. |
| 14 | 15.00 | SH13 | The prompt "Build a responsive analytics dashboard." is typed and sent at 15.95. | The music breathes (pad and hats). 39 thocks. Send: a thock, a big plop and a whoosh. |
| 15 | 16.25 | SH14 | Four file cards fan out in 3D. | A whoosh and 4 staggered mag snaps. The drive groove starts. |
| 16 | 17.00 | SH15 | Diff montage: each file comes forward and its diff slides in (17.0, 17.55, 18.1, 18.65). | Per file: a whoosh, a mag, 5 diff-line ticks and a plop. Rhythmic agent chord stabs. |
| 17 | 19.20 | SH16 | Split screen: `npm run dev` beside the agent steps. Ready at 20.2. | Double whoosh L/R. Thocks, 6 step ticks and boops, and a two-note chime on Ready. |
| 18 | 20.40 | SH17 | Code → interface: lines fly out and become components (20.5, 20.9, 21.3). | Per line: a lift-off whoosh, a landing plop per component, a mag and a stab. |
| 19 | 21.70 | SH18 | The preview grows to fill the frame. **ONE PROMPT. ENDLESS MOMENTUM.** | Two impacts, a riser and a suction. A music silence at 22.9–23.0. |
| 20 | 23.00 | SH19 | **Exploded view** of the dashboard: 7 layers separate in 3D. | The big impact. A downward whoosh and 7 descending plops as the layers part. Half-time weight. |
| 21 | 24.30 | SH20 | **Reconstruction**: each part snaps home every 0.25 s and fills with live data as it lands. The revenue line draws and the bars grow; the view goes flat at 26.0. Hover at 27.7; Export at 28.1. | Per part: a mag and a plop on the 16ths. Number-roll ticks on each metric. A tonal glide for the line. 5 rising plops for the bars. The strongest groove, with the arpeggio up an octave. |
| 22 | 28.50 | SH21 | One continuous pull-back into the editor that built it. **FROM CODE.** (29.35) **TO CREATION.** (29.95) | A long low whoosh and a landing mag. Two impacts and a bell. |
| 23 | 32.00 | SH22 | Montage (Tab, diff, explode, assembly), cutting every 0.75 s. Cube zoom at 35.0, black at 35.95. | Each cut hits. The snare roll accelerates (8ths → 16ths → 32nds → 64ths) under a riser, then a suction into a hard cut. |
| — | 35.95–36.45 | — | Black. | **Silence.** |
| 24 | 36.45 | SH23 | Lockup: official cube and wordmark, **BUILD WHAT'S NEXT.** (37.15), cursor.com (37.55), and the disclaimer. | Sonic logo: the deepest, cleanest impact in the film, then a resolving D major 9 chord and a bell. |
