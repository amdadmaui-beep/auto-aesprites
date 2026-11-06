# Project context for Claude

This repo has two independent parts:

1. **Aseprite auto-build** (repo root): `download.py` and `.github/workflows/auto-build.yml`
   build Aseprite for Windows x64 via GitHub Actions on every push to `main`.
   The root `.gitignore` ignores `src/`, `build/` and `*.txt` for that build.
2. **Video work** (`video/`): a Remotion project for making videos in code.

## New device or account

If the user says they're on a new device or account and asks to "set everything up",
follow `MIGRATION.md`: walk them through reinstalling the listed plugins, skills and
connectors, then the local setup steps. Check what's already installed before suggesting installs.

## Video setup

- Remotion lives in `video/`. Install with `npm i` in `video/` (a cloud SessionStart hook does this automatically).
- Preview: `npm run dev` in `video/`, then open http://localhost:3000.
  In a cloud session the user can't open localhost: render the video or screenshot Studio
  and send the file instead.
- Render: `npx remotion render <CompositionId> out/<name>.mp4` (output in `video/out/`, git-ignored).
- `video/remotion.config.ts` points Remotion at the pre-installed Chromium when it exists
  (`/opt/pw-browsers/...`), because cloud sessions can't download Remotion's own browser.
  On a normal computer that path doesn't exist and Remotion downloads its browser as usual.
- `video/.gitignore` has `!src/` to undo the root `src/` ignore. Keep it.
- `ffmpeg`/`ffprobe` are available in cloud sessions for plain cuts, trims, joins and captions.
  Prefer them over Remotion for simple edits of real footage (cheaper, faster).

## Skills in this repo

`.claude/skills/` holds all the user's skills (32), so they load in any session on this repo.
See `.claude/skills/README.md` for sources and licenses. The repo is private; keep it private.
Plugins that need a service sign-in are listed in `MIGRATION.md`.
"Jackie style" / "Jackie editing style" means the `jackie-edit-style` skill: the user's signature
style for vertical stand-up clips. It belongs to Jackie (a paying client): never use it for a prospect sample.
For any prospect sample, use the `ave-style-lab` skill: it designs a new style per prospect and checks it against
`.claude/skills/ave-style-lab/reserved-styles.json` (Jackie, Brenda and other paying clients).
For websites and UI, use `impeccable` and `frontend-design` so pages don't look generic or AI-made.

## Sound effects

`video/public/sfx/` has 39 named SFX in 5 packs, listed in `sfx-index.json`
(use with `staticFile("sfx/<pack>/<file>.wav")`). They're third-party sounds: avoid the
Mario/Sonic/Metal Gear ones in monetized work.

## Working preferences

- The user works from the Claude app (desktop/web) and mostly in cloud sessions.
- They are cost-conscious (cloud usage, a $100 credit): keep edits to few round trips,
  ask for all changes in one brief, render locally for heavy jobs.
- Fish Audio (AI image/video/voice generation) bills separately: always estimate and get
  approval before generating.
- Keep explanations short and plain; the user isn't a developer by trade.
- When something is blocked and you can't do it yourself (a missing file, font, login, network
  access, a setting), stop and tell the user exactly what to set up and how. Don't guess or fake it.

## Past projects (each on its own branch)

| Project | Branch | What's there |
|---|---|---|
| AVE Studio mascot promo (V1–V3) | `claude/practical-faraday-7a7049` | `ave-promo/`: film source, renders, VO; source footage is in the "AVE Studio Showcase" Google Drive folder (`ave-promo/tools/extract_clips.sh`) |
| Motion graphics showreel (25 s) | `claude/elegant-keller-nekcgv` | `showreel/`: code-driven film, synth score, `reel.mp4` |
| Shot Social reels | `claude/tender-clarke-32xjjk` | `video/src/ShotSocial.tsx`, `video/tools/shotsocial/` caption/cut tools |
| AVE Studio website (prototypes v1–v8) | `claude/upbeat-sagan-jlkd6f` | `website/mockup-v*/`, Pinterest boards in `website/references/`. The live site is its own repo, see below |

To continue one, check out its branch. Don't merge these into `main` without asking.

## AVE Studio website (live)

- Repo: `amdadmaui-beep/ave-studio-website` (Vite + Three.js + Lenis, no framework). Live: https://ave-studio-website.vercel.app
- Vercel auto-deploys every push to `main` (about 30 s). Claude has no Vercel login; the user manages Vercel.
- Contact form: Web3Forms (key in `src/main.js`, public by design) to avestudio.production@gmail.com.
  Web3Forms rejects cloud/server IPs, so a cloud session can't send a real test; the user tests from their own browser.
- Real edits come from the "AVE Studio Showcase" Drive folder (`1kj8XJg3Ot4bveMYElnLNeQbF7tpOpTon`); previews are 6 s muted MP4 loops in `public/clips/w-*.mp4`.
- Brand: ink #0E0E0E, off-white #F3F2EE, lime #C8FF2E (accent only); day/night modes; cursor is the logo's A.

## AVE Studio app (live, Nov 2026)

- Repo: `amdadmaui-beep/ave-hq` (Vite PWA + Supabase), deployed on Vercel from `main`. Its own CLAUDE.md has the rules.
- Has: Today, Leads, Clients, Follow-ups, Analytics, Strategy (weekly sprint from real numbers), Style Lab (looks from every
  Drive edit + Pinterest research, Hooks lab, Builder with motion graph/keyframes, all Google Fonts), Prices, Connections, Joji.
- Data: Supabase (owner-only RLS). Money received is in pesos; prices in USD. Gmail syncs via Google Apps Script
  (`tools/gmail-sync.gs`, copied from the Connections screen).
- Editor round 1 is live in the app (timeline editing). Clip-finder (`video/tools/clipfinder`) was cancelled by the user: don't extend it.
- Still to do: editor render to MP4 (round 2), website visit counter into `site_events` (ave-studio-website), Joji connected to Claude (MCP), urgent SMS via
  UniSMS (needs a local session: unismsapi.com is blocked in the cloud), Instagram (needs a Business account + Facebook Page),
  weekly review automation, Brenda/Debi styles (need their clips in Drive).
