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

`.claude/skills/` holds all the user's skills (29), so they load in any session on this repo.
See `.claude/skills/README.md` for sources and licenses. The repo is private; keep it private.
Plugins that need a service sign-in are listed in `MIGRATION.md`.
"Jackie style" / "Jackie editing style" means the `jackie-edit-style` skill: the user's signature
style for vertical stand-up clips.

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
