import { ImageResponse } from "next/og";

export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function Image() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          background: "#14130F",
          padding: "80px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <svg width="44" height="44" viewBox="0 0 32 32" fill="none">
            <circle cx="16" cy="16" r="13.5" stroke="#FAF9F6" strokeWidth="2" opacity="0.35" />
            <path
              d="M16 2.5 A13.5 13.5 0 0 1 27.8 22"
              stroke="#FAF9F6"
              strokeWidth="2"
              strokeLinecap="round"
            />
            <circle cx="27.8" cy="22" r="2.4" fill="#C1521A" />
          </svg>
          <span style={{ fontSize: 40, fontWeight: 600, color: "#FAF9F6" }}>PAR.</span>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <span style={{ fontSize: 56, fontWeight: 600, color: "#FAF9F6", lineHeight: 1.2 }}>
            今日、買うべき
            <br />
            ゴルフ用品をAIが発見。
          </span>
          <span style={{ fontSize: 26, color: "#E2762F" }}>
            価格の変化を毎日分析。今が買い時かをスコアでお伝えします。
          </span>
        </div>
      </div>
    ),
    { ...size }
  );
}
