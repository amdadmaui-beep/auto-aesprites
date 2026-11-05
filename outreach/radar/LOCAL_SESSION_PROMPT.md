# Paste this into a Claude Code session on your own computer

Set up the AVE lead radar on this computer and run it.

1. In my local clone of `amdadmaui-beep/auto-aesprites`, fetch `origin/claude/upbeat-sagan-jlkd6f` and bring the `outreach/radar/` folder into the branch where my outreach work lives (`claude/compassionate-edison-33k7qx`, which has `outreach/prospects.csv` and `outreach/PLAYBOOK.md`). Only copy that folder; don't merge anything else. Commit it there.
2. Run `python outreach/radar/radar.py` once (use `py` on Windows). Reddit works from my home connection. Show me the report it writes in `outreach/radar/out/` and confirm new leads were added to `outreach/prospects.csv` as `radar-found`. If Reddit returns errors, tell me exactly what it says; don't try to get around a block.
3. Help me set up phone alerts: pick a long random ntfy topic name, put it in `outreach/radar/config.json` as `ntfy_topic`, and tell me which topic to subscribe to in the ntfy app. Send one test alert.
4. Make it run automatically every 2–3 hours while my computer is on. On Windows use Task Scheduler (show me the exact steps or a command); on Mac use a LaunchAgent or cron.
5. For each HOT lead in the first report: open the post, check it's still open, improve the drafted reply with one real detail from the post, and give me the final text to send. Don't send anything yourself.

Context: `outreach/radar/README.md` explains the tool. Our past hiring-post replies got no answers, likely because they were days late, so speed matters: alerts should reach me within a couple of hours of a post going up.
