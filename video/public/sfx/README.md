# Sound effects

39 SFX cut from five creator promo reels (meme, premium, SaaS/UI, trending, typography packs).
`sfx-index.json` lists each sound with its file path and length.

The `.wav` files are stored in this repo, which is **private**. Keep it private:
they're third-party sounds. `full/` has the uncut audio of each source reel.

Use in Remotion:
```tsx
import { Audio, staticFile } from "remotion";
<Audio src={staticFile("sfx/trending-sfx/06-deep-whoosh.wav")} />
```

Licensing: these came from promo videos by other creators, so check each creator's terms before
using them in commercial or monetized work. The game sounds (Mario level up, Sonic coin,
Metal Gear alert) belong to Nintendo, Sega and Konami.
