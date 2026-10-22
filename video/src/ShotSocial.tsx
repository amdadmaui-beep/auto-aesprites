// Shot Social house style, two layouts that follow the agency's references:
// - "ref1" (VIDEO SAMPLE 1): split screen for the whole reel. Supporting footage on
//   top, the speaker below, a yellow divider, subtitles just above the divider.
// - "ref2" (VIDEO SAMPLE 2): split hook with a close-up below, then a burst of
//   full-screen B-roll, then the clean full-screen podcast.
// Positions and the divider colour are measured from the reference files.
// The cut itself (shots, framing, audio) is pre-rendered to public/shotsocial/.
import { AbsoluteFill, Composition, OffthreadVideo, Sequence, staticFile } from "remotion";
import clip1 from "./shotsocial/clip1.json";
import clip2 from "./shotsocial/clip2.json";

type Caption = { text: string; from: number; to: number };
type BRoll = { file: string; from: number; to: number; srcFrom: number; posY: number; zoom?: number };
type ReelData = {
  fps: number;
  durationInFrames: number;
  title: string[];
  splitEnd: number;
  layout: "ref1" | "ref2";
  hookBottom: { file: string; srcFrom: number; posY: number } | null;
  broll: BRoll[];
  captions: Caption[];
};

const FONT = '"SF Pro Display", "Inter Display", "Inter", sans-serif';
const YELLOW = "#EEEF14";
// Subtitle box tops that put the baseline where the references have it.
const SUB_TOP = { ref1: 778, ref2: 1127 };

const Title: React.FC<{ lines: string[] }> = ({ lines }) => (
  <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
      {lines.map((line) => (
        <div
          key={line}
          style={{
            fontFamily: FONT,
            fontWeight: 800,
            fontSize: 64,
            lineHeight: "70px",
            color: "#000",
            background: "#fff",
            borderRadius: 12,
            padding: "2px 16px",
            marginTop: -2,
            letterSpacing: -0.5,
            whiteSpace: "nowrap",
          }}
        >
          {line}
        </div>
      ))}
    </div>
  </AbsoluteFill>
);

// Speaker crop for the bottom panel: rows 412-1372 of the full speaker frame,
// which puts the eyes about 30% down the panel (the reference is ~25%; a little
// more headroom keeps the host's hat in frame).
const SPEAKER_TOP = 412;

const YellowLine: React.FC = () => (
  <div style={{ position: "absolute", top: 955, left: 0, width: "100%", height: 10, background: YELLOW }} />
);

const Panel: React.FC<{ top: number; children: React.ReactNode }> = ({ top, children }) => (
  <div style={{ position: "absolute", top, width: 1080, height: 960, overflow: "hidden" }}>{children}</div>
);

// zoom > 1 punches in from the top, e.g. to keep a clip's own text clear of the subtitle.
const Clip: React.FC<{ file: string; srcFrom: number; posY: number; zoom?: number }> = ({ file, srcFrom, posY, zoom = 1 }) => (
  <OffthreadVideo
    src={staticFile(`shotsocial/broll/${file}.mp4`)}
    trimBefore={srcFrom}
    muted
    style={{
      width: "100%",
      height: "100%",
      objectFit: "cover",
      objectPosition: `50% ${posY}%`,
      transform: `scale(${zoom})`,
      transformOrigin: "50% 0%",
    }}
  />
);

const Subtitle: React.FC<{ text: string; top: number }> = ({ text, top }) => (
  <AbsoluteFill>
    <div
      style={{
        position: "absolute",
        top,
        width: "100%",
        textAlign: "center",
        fontFamily: FONT,
        fontWeight: 700,
        fontSize: 46,
        color: "#fff",
        textShadow: "0 0 3px rgba(0,0,0,0.9), 0 0 9px rgba(0,0,0,0.8), 0 0 18px rgba(0,0,0,0.65)",
        whiteSpace: "nowrap",
      }}
    >
      {text}
    </div>
  </AbsoluteFill>
);

const Reel: React.FC<{ name: string; data: ReelData }> = ({ name, data }) => {
  const splitFrames = Math.round(data.splitEnd * data.fps);
  const speaker = staticFile(`shotsocial/${name}.mp4`);
  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      {data.layout === "ref1" ? (
        <>
          <Panel top={0}>
            <OffthreadVideo src={staticFile(`shotsocial/${name}_top.mp4`)} muted />
          </Panel>
          <Panel top={960}>
            <OffthreadVideo src={speaker} style={{ position: "absolute", top: -SPEAKER_TOP, width: 1080, height: 1920 }} />
          </Panel>
          <YellowLine />
        </>
      ) : (
        <>
          <OffthreadVideo src={speaker} />
          {data.hookBottom ? (
            <Sequence durationInFrames={splitFrames} layout="none">
              <Panel top={960}>
                <Clip {...data.hookBottom} />
              </Panel>
              <YellowLine />
            </Sequence>
          ) : null}
          {data.broll.map((b) => (
            <Sequence key={b.from} from={b.from} durationInFrames={b.to - b.from}>
              <Clip {...b} />
            </Sequence>
          ))}
        </>
      )}
      {/* Neither reference shows subtitles while the hook title is up. */}
      {data.captions
        .filter((c) => c.to > splitFrames)
        .map((c) => {
          const from = Math.max(c.from, splitFrames);
          return (
            <Sequence key={c.from} from={from} durationInFrames={c.to - from} layout="none">
              <Subtitle text={c.text} top={SUB_TOP[data.layout]} />
            </Sequence>
          );
        })}
      <Sequence durationInFrames={splitFrames} layout="none">
        <Title lines={data.title} />
      </Sequence>
    </AbsoluteFill>
  );
};

export const ShotSocialReels: React.FC = () => (
  <>
    {(
      [
        ["ShotSocial-Fertility", "clip1", clip1],
        ["ShotSocial-Cake", "clip2", clip2],
      ] as const
    ).map(([id, name, data]) => (
      <Composition
        key={id}
        id={id}
        component={Reel}
        durationInFrames={data.durationInFrames}
        fps={data.fps}
        width={1080}
        height={1920}
        defaultProps={{ name, data: data as ReelData }}
      />
    ))}
  </>
);
