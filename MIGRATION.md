# Moving this setup to a new computer or account

Everything that can live in this repo is here. A few things belong to a claude.ai account
and have to be set up again on the new account.

## Saved in this repo (comes along automatically)

| What | Where |
|---|---|
| Project context and working preferences for Claude | `CLAUDE.md` |
| Remotion + motion-studio skills (13 skills) | `.claude/skills/` |
| Remotion video project, already configured for cloud sessions | `video/` |
| Cloud auto-setup (installs `video/` packages at session start) | `.claude/settings.json`, `.claude/hooks/session-start.sh` |
| Aseprite auto-build | `download.py`, `.github/workflows/auto-build.yml` |

Note: the work is on branch `claude/video-editing-local-cloud-l6e5p0`. New sessions start
from `main`, so merge this branch into `main` to make it the default. Pushing to `main`
also starts the Aseprite build workflow.

## Set up again on the new account (claude.ai)

These are tied to an account and can't be carried in a repo. Reinstall them from
**claude.ai -> Customize** (Plugins / Skills / Connectors). Search by the name shown.

### Plugins (Anthropic plugin directory)

| Plugin | Gives you |
|---|---|
| Remotion | Remotion video skills (also saved in this repo) |
| Design (Anthropic) | design critique, design system, UX copy, accessibility, user research |
| Adaptive Agent | user profile memory, skill review |
| Consistent UI | UI consistency audit |
| SocialRobot | social post scheduling (needs SocialRobot sign-in) |
| Postiz | social media scheduling across 28+ platforms (needs a Postiz account/API key) |
| Browser Use | real browser control |
| Playwright | browser automation and testing |

Optional, suggested for the Prospect hunter work: **Sales**, **Vibe Prospecting**,
**Cold Email, LinkedIn Outreach & Deliverability**.

### Skills from plugins you added

agent-reach (web/social research), hindsight-local and hindsight-architect (memory),
motion-studio-rules (also saved in this repo).

### Built-in Anthropic skills (every account has these, nothing to do)

docs, docx, pdf, pptx, xlsx, deep-research, learn, morning, skill-creator,
import-memory, computer-use, built-in-browser, chrome-browser.

### Connectors (sign in again)

GitHub (repo access), Gmail, Google Drive, Fish Audio.
Design-plugin connectors (Figma, Notion, Slack, Linear, Atlassian, Intercom, Asana)
only if you use them.

## On the new computer

1. Install **Git** and **Node.js** (LTS) from git-scm.com and nodejs.org.
2. Get the project:
   ```bash
   git clone https://github.com/amdadmaui-beep/auto-aesprites
   cd auto-aesprites
   git checkout claude/video-editing-local-cloud-l6e5p0   # skip once merged into main
   cd video
   npm i
   npm run dev        # preview at http://localhost:3000
   ```
3. Install the Claude desktop app, sign in, and open this folder (or start cloud sessions
   on this repo from claude.ai/code). Claude reads `CLAUDE.md` and `.claude/skills/` automatically.

## What can't be moved

- **Past conversations and cloud sessions** stay with the account they were made in.
  `CLAUDE.md` carries the important context instead.
- **Usage credit** (the $100 cloud credit) belongs to the original account.
- **Installed plugins, connectors and sign-ins** must be added again (see above).
