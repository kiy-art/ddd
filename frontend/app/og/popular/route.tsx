import { ImageResponse } from "next/og";

import { CATEGORY_LABELS, getRakutenRanking } from "@/lib/api";
import { BrandMark, CtaPill, HookChip, OG_API_TIMEOUT_MS, OG_SIZE, POP, fetchImageDataUri, ogFonts, truncate, withTimeout, yen } from "@/lib/og";

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

async function fallback() {
  const title = "いま売れてるゴルフ用品ランキング";
  const fonts = await ogFonts(["売れ筋ランキング", title, "1位を見る", "毎日更新"]);
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          background: POP.bg,
          padding: "48px 60px 40px",
          fontFamily: "PAR",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <BrandMark size={36} />
          <HookChip text="売れ筋ランキング" />
        </div>
        <span style={{ display: "flex", fontSize: 80, fontWeight: 900, color: POP.yellow, lineHeight: 1.2 }}>{title}</span>
        <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
          <CtaPill text="1位を見る" />
          <span style={{ display: "flex", fontSize: 22, fontWeight: 500, color: POP.gray }}>par-gear.com ・ 毎日更新</span>
        </div>
      </div>
    ),
    { ...OG_SIZE, fonts }
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
  const names = top.map((e) => truncate(cleanName(e.name), 14));
  const title = `いま売れてる${label}`;
  const stamp = `${date}時点・楽天市場`;
  const cta = "値動きと買い時を見る";
  const fonts = await ogFonts([title, "TOP3", stamp, cta, label, ...names, ...top.map((e) => yen(e.price))]);

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          background: POP.bg,
          padding: "36px 48px 32px",
          fontFamily: "PAR",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: 18 }}>
            <span style={{ display: "flex", fontSize: 60, fontWeight: 900, color: POP.white }}>{title}</span>
            <span style={{ display: "flex", fontSize: 76, fontWeight: 900, color: POP.yellow }}>TOP3</span>
          </div>
          <BrandMark size={32} />
        </div>
        <div style={{ display: "flex", gap: 22, marginTop: 14, flex: 1 }}>
          {top.map((e, i) => (
            <div
              key={e.rank}
              style={{
                display: "flex",
                flexDirection: "column",
                flex: 1,
                background: "#FFFFFF",
                borderRadius: 26,
                padding: "14px 18px 14px",
                position: "relative",
              }}
            >
              <div style={{ display: "flex", height: 215, alignItems: "center", justifyContent: "center" }}>
                {photos[i] ? (
                  // eslint-disable-next-line @next/next/no-img-element -- satori renders plain <img>
                  <img src={photos[i] as string} width={215} height={215} style={{ objectFit: "contain" }} alt="" />
                ) : (
                  <span style={{ display: "flex", fontSize: 26, color: "#5B6B64" }}>{label}</span>
                )}
              </div>
              <div
                style={{
                  display: "flex",
                  position: "absolute",
                  top: -10,
                  left: -10,
                  width: 78,
                  height: 78,
                  borderRadius: 999,
                  background: i === 0 ? POP.red : MEDALS[i],
                  border: `4px solid ${POP.white}`,
                  color: i === 1 ? POP.black : POP.white,
                  fontSize: 44,
                  fontWeight: 900,
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                {e.rank}
              </div>
              <span style={{ display: "flex", marginTop: 6, fontSize: 24, fontWeight: 900, color: POP.black }}>{names[i]}</span>
              <span style={{ display: "flex", fontSize: 44, fontWeight: 900, color: POP.red, lineHeight: 1.15 }}>{yen(e.price)}</span>
            </div>
          ))}
        </div>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 18 }}>
          <CtaPill text={cta} />
          <span style={{ display: "flex", fontSize: 22, fontWeight: 500, color: POP.gray }}>{`${stamp} ・ par-gear.com`}</span>
        </div>
      </div>
    ),
    { ...OG_SIZE, fonts, headers: { "Cache-Control": "public, max-age=3600, s-maxage=3600" } }
  );
}
