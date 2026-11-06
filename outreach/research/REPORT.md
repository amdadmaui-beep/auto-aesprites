# Target research: fast-growing comedians and podcasters (Nov 2026)

**What this is.** A sourced list of comedians and comedy podcasts that are rising right now and are a fit for AVE
(they have long sets or episodes, and are growing fast enough to want clips but small enough not to have a clip team),
plus what the evidence says makes stand-up clips work. Files: `targets.csv` (79 targets, every row has its source link),
`import-targets.sql` (adds them to the AVE Studio app as cold leads).

## Honest limits
- The roadmap asked for ~200. I found **79 that are sourced and fit**. TikTok and Pinterest hide their data behind a login
  from cloud servers, and several rankings (Time Out L.A./Chicago, Vulture, JFL New Faces) weren’t online at their usual address.
  I didn’t pad the list from memory. More can be added the same way on request.
- Growth numbers are a snapshot from InfluData’s public rankings (monthly follower growth) and CastFox’s Apple chart movement.
  Check a person’s current numbers before pitching.
- Big names were left out on purpose (Jimmy Carr, Hasan Minhaj, Anthony Jeselnik, DeRay Davis, Rickey Smiley, Justin Willman,
  Ben Marshall, and Comedyville’s headliners like Matt Rife and Marcello Hernández): they already have teams.

## What works for stand-up clips (with sources)
1. **Captions, burned in and animated.** 80.2% of viral-tier clips burn captions in; 78.6% animate them
   (OpusClip, 13.5M clips, Jan–Mar 2026) — [opus.pro](https://www.opus.pro/blog/anatomy-of-a-viral-tiktok-2026).
   Captions should read along without spoiling the punchline — [Cramer Comedy Newsletter](https://cramercomedynewsletter.substack.com/p/guest-post-why-these-comedians-went).
2. **Payoff up front.** The weakest hooks are “let me tell you about the time I…” story set-ups; the best put the outcome in the
   first 3 seconds (OpusClip). Think about how the first 5 seconds land for someone who doesn’t know you or stand-up —
   former TikTok analyst David Zucker via [Funny How](https://funnyhow.substack.com/p/tiktok-guru-start-posting-longer).
3. **Length: aim for ~30–45 s, but a great bit can run long.** Viral median 41 s; 15–60 s over-represented, 60–90 s
   under-represented (OpusClip). Zucker shows a 3 min 22 s musical-comedy clip at 2.3M views: length isn’t the problem, dead air is.
4. **The goal is shares, not views.** Write the clip so it gets sent to a group chat of strangers (Zucker, Funny How).
   Share and save rates are the signal: >8% like rate and >1% save rate is very high at scale (Cramer).
5. **Clubs book TikTok numbers.** Clubs book comedians with big followings to sell tickets — [NPR via KUOW](https://kuow.org/stories/tiktok-is-upending-both-the-business-and-craft-of-stand-up-comedy).
   That’s the pitch: clips sell tickets.
6. **Podcasts: niche and relaunched shows are climbing fastest**, and short video keeps feeding long-form audio —
   [CastFox](https://www.castfox.net/blog/best-growing-comedy-podcasts-2026-part-1).

**How AVE already matches:** every AVE edit uses animated burned-in captions, a hook title in the first 3 seconds, one key word
highlighted, and lands on the punchline. Clip-finder now picks 20–60 s moments that end on a laugh.

## The list (summary)
| Group | Count | Source |
|---|---|---|
| Time Out “Comedians to Watch 2026” | 12 | [timeout.com](https://www.timeout.com/usa/comedy/comedians-to-watch-in-2026) |
| GOLD Comedy “26 Comedians to Watch in 2026” | 26 | [goldcomedy.com](https://goldcomedy.com/resources/26-comedians-to-watch-in-2026/) |
| Fast-climbing comedy podcasts (not mega-shows) | 7 | CastFox [part 1](https://www.castfox.net/blog/best-growing-comedy-podcasts-2026-part-1), [part 2](https://www.castfox.net/blog/best-growing-comedy-podcasts-2026-part-2) |
| Comedians growing on TikTok (LA, NYC, US, UK, Canada, Australia) | 34 | InfluData rankings (links per row) |

**Good fit (27):** growing ≥2%/month on TikTok, a podcast climbing the charts, or a rising comic with taped sets.
Start with these: find their latest set, pre-cut a free sample with Clip-finder, and send it.
**Warm-up (52):** follow and engage first; pitch when they post a set or special.

## Next steps
1. Run `import-targets.sql` in Supabase (SQL Editor) to put all 79 in the app as cold leads with notes and sources.
2. Pick 5 “good fit” names a week (fits the sprint’s targets), run their set through Clip-finder, send samples.
