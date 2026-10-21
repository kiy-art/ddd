import { ImageResponse } from "next/og";

import { CATEGORY_LABELS, getRakutenRanking } from "@/lib/api";
import { BrandMark, OG_API_TIMEOUT_MS, OG_COLORS, OG_SIZE, fetchImageDataUri, truncate, withTimeout, yen } from "@/lib/og";

// Share image for /popular (X posts link here as /popular?category=driver).
// A file-based opengraph-image can't read the query string, so the page's
// generateMetadata points og:image at this route with the category.
// 2026-10-20: the posts showed the plain default card (text only); this shows
// the real top-3 product photos, ranks and prices instead.

const MEDALS = ["#C9A227", "#A8B3B0", "#B0774A"];

// Rakuten listing titles carry shop promos ("10/20 限定 抽選で最大100％Pバック",
// 【送料無料】...). Strip the obvious ones so the card shows the product.
function cleanName(raw: string): string {
  return raw
    .replace(/【[^】]*】|\[[^\]]*\]|［[^］]*］/g, " ")
    .replace(/^\s*\d{1,2}\/\d{1,2}\s*限定[^ ]*\s*/, "")
    .replace(/抽選で[^ ]*?(Pバック|ポイントバック|還元)\s*/g, "")
    .replace(/ポイント\d+倍|P\d+倍|送料無料|あす楽|即納/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function fallback() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          background: OG_COLORS.ink,
          padding: "72px",
        }}
      >
        <BrandMark />
        <span style={{ display: "flex", fontSize: 64, fontWeight: 700, color: OG_COLORS.paper, lineHeight: 1.25 }}>
          楽天の売れ筋ゴルフ用品ランキング
        </span>
        <span style={{ display: "flex", fontSize: 26, color: OG_COLORS.muted }}>par-gear.com ・ 毎日更新</span>
      </div>
    ),
    { ...OG_SIZE }
  );
}

export async function GET(request: Request) {
  const category = new URL(request.url).searchParams.get("category") ?? "driver";
  const data = await withTimeout(getRakutenRanking(3, { signal: AbortSignal.timeout(OG_API_TIMEOUT_MS) }));
  const block = data?.find((c) => c.category === category) ?? data?.[0];
  if (!block || block.entries.length === 0) return fallback();

  const label = CATEGORY_LABELS[block.category] ?? "ゴルフ用品";
  const top = block.entries.slice(0, 3);
  const photos = await Promise.all(top.map((e) => fetchImageDataUri(e.image_url)));
  const date = new Date(block.fetched_at.endsWith("Z") ? block.fetched_at : `${block.fetched_at}Z`).toLocaleDateString("ja-JP", {
    timeZone: "Asia/Tokyo",
    month: "numeric",
    day: "numeric",
  });

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          background: OG_COLORS.ink,
          padding: "40px 52px 36px",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <BrandMark size={34} />
          <span style={{ display: "flex", fontSize: 24, color: OG_COLORS.muted }}>{date}時点 ・ 楽天市場</span>
        </div>
        <span style={{ display: "flex", marginTop: 14, fontSize: 52, fontWeight: 700, color: OG_COLORS.paper }}>
          {`売れ筋${label} TOP3`}
        </span>
        <div style={{ display: "flex", gap: 24, marginTop: 22, flex: 1 }}>
          {top.map((e, i) => (
            <div
              key={e.rank}
              style={{
                display: "flex",
                flexDirection: "column",
                flex: 1,
                background: "#FFFFFF",
                border: "2px solid #D1FAE5",
                borderRadius: 28,
                padding: "16px 18px 18px",
                position: "relative",
              }}
            >
              <div style={{ display: "flex", height: 230, alignItems: "center", justifyContent: "center" }}>
                {photos[i] ? (
                  // eslint-disable-next-line @next/next/no-img-element -- satori renders plain <img>
                  <img src={photos[i] as string} width={230} height={230} style={{ objectFit: "contain" }} alt="" />
                ) : (
                  <span style={{ display: "flex", fontSize: 26, color: OG_COLORS.muted }}>{label}</span>
                )}
              </div>
              <div
                style={{
                  display: "flex",
                  position: "absolute",
                  top: 14,
                  left: 14,
                  width: 60,
                  height: 60,
                  borderRadius: 999,
                  background: MEDALS[i] ?? OG_COLORS.accent,
                  color: i === 2 ? "#FFFFFF" : "#14201B",
                  fontSize: 32,
                  fontWeight: 700,
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                {e.rank}
              </div>
              <span style={{ display: "flex", marginTop: 10, fontSize: 24, fontWeight: 600, color: OG_COLORS.paper }}>
                {truncate(cleanName(e.name), 15)}
              </span>
              <span style={{ display: "flex", marginTop: 6, fontSize: 38, fontWeight: 700, color: OG_COLORS.accent }}>
                {yen(e.price)}
              </span>
            </div>
          ))}
        </div>
        <span style={{ display: "flex", marginTop: 16, fontSize: 22, color: OG_COLORS.muted }}>
          par-gear.com ・ 価格推移と買い時をチェック
        </span>
      </div>
    ),
    { ...OG_SIZE, headers: { "Cache-Control": "public, max-age=3600, s-maxage=3600" } }
  );
}
