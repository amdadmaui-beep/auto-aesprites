# AVE promo (reverse-engineered from a vertical brand reel)

`AVE_Promo_9x16.mp4`: 1080x1920, 60 fps, 15.6 s. Beat-for-beat rebuild of a reference brand promo, made for AVE Studio:
AVE's Instagram profile and work, an AVE app icon and cube, AVE lime instead of the reference brand's blue, AVE end
logo. Audio is the reference's track (`film/audio_ref.wav`, not committed).

| Time (s) | Beat |
|---|---|
| 0.0-1.4 | Phone spins in from the dark (back, then front) in real CSS 3D with edge thickness, settles on AVE's Instagram profile |
| 1.2-2.4 | Tilts back; six posts (our work) fly out of the screen in 3D and fall back |
| 1.9-3.4 | Camera skims across the profile and dives at the avatar (pivot set on the avatar) |
| 3.3-4.3 | Lime hologram rings around the avatar, the AVE app icon rises |
| 4.3-6.5 | Lime void: spinning AVE cube with orbiting "Ahhh", outlined type drifting behind |
| 6.5-9.25 | Grey spotlight, 3D kinetic lyrics; black frame with a bulging oval for "Dragon Balls"; "Bitch I feel like" |
| 9.25-13 | Glowing words on black (red, yellow, blue, white, dripping red), "life is cell", prison bars slide in |
| 13.1-15.6 | AVE STUDIO logo glows in |

Rebuild from `film/`: `node render.mjs --video=build/video.mp4 --sub=2`, then mux with the audio.
