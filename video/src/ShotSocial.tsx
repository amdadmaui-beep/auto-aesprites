// Shot Social house style: split-screen hook with a yellow divider and a
// white-box title, then bold white subtitles with a dark halo. B-roll plays in
// the top half over the speaker, split by the same yellow line.
// The cut itself (shots, framing, audio) is pre-rendered to public/shotsocial/.
import { AbsoluteFill, Composition, OffthreadVideo, Sequence, staticFile, useCurrentFrame } from "remotion";
import clip1 from "./shotsocial/clip1.json";
import clip2 from "./shotsocial/clip2.json";

type Caption = { text: string; from: number; to: number };
type BRoll = { file: string; from: number; to: number; srcFrom: number; posY: number };
type ReelData = {
  fps: number;
  durationInFrames: number;
  title: string[];
  splitEnd: number;
  broll: BRoll[];
  captions: Caption[];
};

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

// Speaker crop for the bottom half during B-roll: rows 330-1290 of the full frame,
// which keeps the face in the upper part of the half like the reference.
const SPEAKER_TOP = 330;

const YellowLine: React.FC = () => (
  <div style={{ position: "absolute", top: 955, left: 0, width: "100%", height: 10, background: YELLOW }} />
);

// Above the yellow line while B-roll is up, lower-middle otherwise.
const Subtitle: React.FC<{ text: string; start: number; broll: BRoll[] }> = ({ text, start, broll }) => {
  const frame = start + useCurrentFrame();
  const split = broll.some((b) => frame >= b.from && frame < b.to);
  return (
    <AbsoluteFill>
      <div
        style={{
          position: "absolute",
          top: split ? 790 : 1130,
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
};

const Reel: React.FC<{ name: string; data: ReelData }> = ({ name, data }) => {
  const splitFrames = Math.round(data.splitEnd * data.fps);
  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      <OffthreadVideo src={staticFile(`shotsocial/${name}.mp4`)} />
      {/* Real-life/influencer B-roll, muted, top half; the speaker stays in the bottom half. */}
      {data.broll.map((b) => (
        <Sequence key={b.from} from={b.from} durationInFrames={b.to - b.from}>
          <div style={{ position: "absolute", top: 0, width: 1080, height: 960, overflow: "hidden" }}>
            <OffthreadVideo
              src={staticFile(`shotsocial/broll/${b.file}.mp4`)}
              trimBefore={b.srcFrom}
              muted
              style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: `50% ${b.posY}%` }}
            />
          </div>
          <div style={{ position: "absolute", top: 960, width: 1080, height: 960, overflow: "hidden" }}>
            <OffthreadVideo
              src={staticFile(`shotsocial/${name}.mp4`)}
              trimBefore={b.from}
              muted
              style={{ position: "absolute", top: -SPEAKER_TOP, width: 1080, height: 1920 }}
            />
          </div>
          <YellowLine />
        </Sequence>
      ))}
      <Sequence durationInFrames={splitFrames} layout="none">
        <YellowLine />
      </Sequence>
      {/* The reference shows no subtitles while the hook title is up. */}
      {data.captions
        .filter((c) => c.to > splitFrames)
        .map((c) => {
          const from = Math.max(c.from, splitFrames);
          return (
            <Sequence key={c.from} from={from} durationInFrames={c.to - from} layout="none">
              <Subtitle text={c.text} start={from} broll={data.broll} />
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
