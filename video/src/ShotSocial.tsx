// Shot Social house style: split-screen hook with a yellow divider and a
// white-box title, then plain white subtitles with a soft dropshadow.
// The cut itself (shots, framing, audio) is pre-rendered to public/shotsocial/.
import { AbsoluteFill, Composition, OffthreadVideo, Sequence, staticFile } from "remotion";
import clip1 from "./shotsocial/clip1.json";
import clip2 from "./shotsocial/clip2.json";

type Caption = { text: string; from: number; to: number };
type ReelData = {
  fps: number;
  durationInFrames: number;
  title: string[];
  splitEnd: number;
  captions: Caption[];
};

// Stand-in for SF Pro Display; swap the first name in if the font is installed.
const FONT = '"SF Pro Display", "Inter Display", "Inter", sans-serif';
const YELLOW = "#F5F50A";

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

const Subtitle: React.FC<{ text: string }> = ({ text }) => (
  <AbsoluteFill>
    <div
      style={{
        position: "absolute",
        top: 1130,
        width: "100%",
        textAlign: "center",
        fontFamily: FONT,
        fontWeight: 600,
        fontSize: 46,
        color: "#fff",
        textShadow: "0 1px 4px rgba(0,0,0,0.55), 0 0 12px rgba(0,0,0,0.35)",
        whiteSpace: "nowrap",
      }}
    >
      {text}
    </div>
  </AbsoluteFill>
);

const Reel: React.FC<{ name: string; data: ReelData }> = ({ name, data }) => {
  const splitFrames = Math.round(data.splitEnd * data.fps);
  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      <OffthreadVideo src={staticFile(`shotsocial/${name}.mp4`)} />
      <Sequence durationInFrames={splitFrames} layout="none">
        <div style={{ position: "absolute", top: 955, left: 0, width: "100%", height: 10, background: YELLOW }} />
      </Sequence>
      {/* The reference shows no subtitles while the hook title is up. */}
      {data.captions
        .filter((c) => c.to > splitFrames)
        .map((c) => {
          const from = Math.max(c.from, splitFrames);
          return (
            <Sequence key={c.from} from={from} durationInFrames={c.to - from} layout="none">
              <Subtitle text={c.text} />
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
