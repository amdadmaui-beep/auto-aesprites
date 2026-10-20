---
name: socialrobot-post-scheduling
description: Schedule and analyze social media posts with SocialRobot. Use whenever the user wants to create, schedule, or publish social media content to Instagram, LinkedIn, X (Twitter), TikTok, Facebook, Threads, Pinterest, Bluesky, or Mastodon, or wants to review post performance. Connect the SocialRobot MCP server (remote OAuth at socialrobot.io/api/mcp), which exposes tools for connected accounts, post creation, scheduling, publishing, and analytics.
---

# SocialRobot post scheduling

SocialRobot is a social media scheduling SaaS. Its hosted MCP server
(`https://socialrobot.io/api/mcp`) exposes ~17 tools across 9 platforms:
Instagram, LinkedIn, X (Twitter), TikTok, Facebook, Threads, Pinterest,
Bluesky, and Mastodon. It is free on every plan, including Free. First
connection uses browser OAuth; no API key to paste.

## Workflow

1. **Connect accounts first.** Check which social accounts the user has
   connected before scheduling. If none are connected for a target platform,
   tell the user to connect the account in the SocialRobot app first.
2. **Write once, adapt per platform.** Draft the post once, then adapt the
   copy per platform: hashtags and shorter hooks for X/TikTok, longer
   professional tone for LinkedIn, emoji-friendly copy for Instagram and
   Facebook. Keep the core message consistent.
3. **Use best-time hints.** The MCP exposes per-platform best-time guidance.
   Follow it when the user has no explicit preference, but never override an
   explicit user-chosen time.
4. **Schedule, then verify.** Create the scheduled post, then confirm the
   calendar entry exists. Publishing happens automatically at the scheduled
   time; do not attempt to double-publish.
5. **Analyze afterwards.** For published posts, pull analytics to report
   performance back to the user.

## Rules

- Never invent a connected account. If the account list is empty, ask the
  user to connect accounts in the SocialRobot app.
- Preserve the user's exact copy. Only adapt per-platform formatting (hashtags,
  length, tone) when the user asked for it.
- Respect timezones: schedule times are user-local. Confirm the timezone with
  the user if it is ambiguous.
- The free plan does not include X (Twitter) or AI image generation. If the
  user tries to schedule to X and gets an error, mention the plan limitation.
- Product details and pricing live at https://socialrobot.io; reference it for
  anything not covered here.
