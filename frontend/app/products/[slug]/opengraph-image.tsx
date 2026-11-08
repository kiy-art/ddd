import { ImageResponse } from "next/og";

import { getProduct } from "@/lib/api";
import { verdictInfo } from "@/lib/buySignal";
import { getFallbackValueScore } from "@/lib/fallbackScore";
import { getModelCycleInsight } from "@/lib/modelCycle";
import {
  BrandMark,
  Footer,
  HookChip,
  OG_API_TIMEOUT_MS,
  OG_COLORS,
  OG_SIZE,
  PhotoTile,
  dropHeadline,
  fetchImageDataUri,
  findRecentDrop,
  productShareFacts,
  truncate,
  withTimeout,
  yen,
} from "@/lib/og";

export const alt = "PAR. 価格推移と買い時判定";
export const size = OG_SIZE;
export const contentType = "image/png";

export default async function Image({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const product = await withTimeout(getProduct(slug, { signal: AbortSignal.timeout(OG_API_TIMEOUT_MS) }));

  if (!product) {
    // Backend asleep/unreachable or unknown slug: still a branded card,
    // never an error (an error is what X renders as a grey placeholder).
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
          <span style={{ display: "flex", fontSize: 60, fontWeight: 700, color: OG_COLORS.paper, lineHeight: 1.25 }}>
            そのギア、今が買い時？
          </span>
          <Footer right="価格推移と買い時判定を毎日更新" />
        </div>
      ),
      { ...size }
    );
  }

  const facts = productShareFacts(product);
  const photo = await fetchImageDataUri(product.image_url);
  const drop = findRecentDrop(product);

  // 2026-11-08: a recent real price drop gets a hook-first card - the
  // headline and the before→after prices are what make people tap it on X.
  if (drop) {
    return new ImageResponse(
      (
        <div
          style={{
            width: "100%",
            height: "100%",
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
            backgroundImage: "linear-gradient(135deg, #FFF1F2 0%, #FFF7ED 55%, #ECFDF5 100%)",
            padding: "48px 60px",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <BrandMark size={34} />
            <div
              style={{
                display: "flex",
                background: "#E11D48",
                color: "#FFFFFF",
                fontSize: 30,
                fontWeight: 700,
                padding: "10px 28px",
                borderRadius: 999,
              }}
            >
              {`値下がり -${drop.percentDown}%`}
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 40 }}>
            <div style={{ display: "flex", flexDirection: "column", flex: 1 }}>
              <span style={{ display: "flex", fontSize: dropHeadline(drop).length > 11 ? (photo ? 50 : 60) : 64, fontWeight: 700, color: "#E11D48", lineHeight: 1.15 }}>
                {dropHeadline(drop)}
              </span>
              <span style={{ display: "flex", fontSize: 28, color: OG_COLORS.paper, marginTop: 14, lineHeight: 1.3 }}>
                {truncate(`${product.brand} ${product.name}`, photo ? 26 : 36)}
              </span>
              <div style={{ display: "flex", alignItems: "center", gap: 18, marginTop: 22 }}>
                <span
                  style={{
                    display: "flex",
                    fontSize: 40,
                    color: OG_COLORS.muted,
                    textDecoration: "line-through",
                  }}
                >
                  {yen(drop.before)}
                </span>
                <span style={{ display: "flex", fontSize: 40, color: OG_COLORS.muted }}>→</span>
                <span style={{ display: "flex", fontSize: 84, fontWeight: 700, color: OG_COLORS.paper }}>
                  {yen(drop.after)}
                </span>
              </div>
              <span style={{ display: "flex", fontSize: 26, color: OG_COLORS.accent, marginTop: 14, fontWeight: 600 }}>
                {`${drop.stableDays}日ずっと${yen(drop.before)}だったのに…`}
              </span>
            </div>
            {photo && <PhotoTile src={photo} size={360} />}
          </div>

          <Footer right="毎日の楽天の価格記録より" />
        </div>
      ),
      { ...size }
    );
  }

  const score = facts.hasReliableTrend ? product.buy_signal_score : null;
  // Same fallback ladder the product page itself uses (AiBuySignal.tsx /
  // PriceTimeline.tsx): a real MSRP-based score, then a model-cycle read.
  const fallback = !facts.hasReliableTrend
    ? getFallbackValueScore({
        msrp: product.msrp,
        current_price: product.current_price,
        release_date: product.release_date,
      })
    : null;
  const cycleInsight =
    !facts.hasReliableTrend && !fallback
      ? getModelCycleInsight({ release_date: product.release_date, is_current_generation: product.is_current_generation })
      : null;

  const signalLabel =
    score !== null
      ? `買い時スコア ${score}/100（${verdictInfo(product.buy_score).label}）`
      : fallback
        ? `定価からのお得度 ${fallback.score}/100`
        : cycleInsight
          ? `${cycleInsight.stageLabel}（${cycleInsight.tier === "fact" ? "FACT" : "AI推測"}）`
          : null;

  const savingsLine =
    facts.savingsYen !== null
      ? `定価より${yen(facts.savingsYen)}安い（-${facts.savingsPercent}%）`
      : facts.hasReliableTrend && product.price_change_percent !== null && product.price_change_percent !== 0
        ? `30日平均比 ${product.price_change_percent > 0 ? "+" : ""}${product.price_change_percent}%`
        : null;

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
          padding: "56px 64px",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <BrandMark size={36} />
          {facts.hook && <HookChip text={facts.hook} />}
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 48 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 12, flex: 1 }}>
            <span style={{ display: "flex", fontSize: 28, color: OG_COLORS.accentLight }}>{product.brand}</span>
            <span
              style={{ display: "flex", fontSize: 50, fontWeight: 700, color: OG_COLORS.paper, lineHeight: 1.2 }}
            >
              {truncate(product.name, photo ? 30 : 40)}
            </span>
            <span style={{ display: "flex", fontSize: 88, fontWeight: 700, color: OG_COLORS.paper, marginTop: 8 }}>
              {yen(product.current_price)}
            </span>
            {savingsLine && (
              <span style={{ display: "flex", fontSize: 32, fontWeight: 600, color: OG_COLORS.accentLight }}>
                {savingsLine}
              </span>
            )}
            {photo && signalLabel && (
              <span style={{ display: "flex", fontSize: 24, color: OG_COLORS.muted, marginTop: 4 }}>{signalLabel}</span>
            )}
          </div>

          {photo ? (
            <PhotoTile src={photo} size={380} />
          ) : score !== null || fallback ? (
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                width: 240,
                height: 240,
                borderRadius: 120,
                border: `10px ${score !== null ? "solid" : "dashed"} ${OG_COLORS.accent}`,
              }}
            >
              <span style={{ display: "flex", fontSize: 80, fontWeight: 700, color: OG_COLORS.paper }}>
                {score !== null ? score : fallback?.score}
              </span>
              <span style={{ display: "flex", fontSize: 18, color: OG_COLORS.accentLight, letterSpacing: 2 }}>
                {score !== null ? verdictInfo(product.buy_score).label : "定価からのお得度"}
              </span>
            </div>
          ) : (
            cycleInsight && (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  width: 280,
                  minHeight: 220,
                  borderRadius: 32,
                  border: `8px dashed ${OG_COLORS.accent}`,
                  padding: "0 16px",
                }}
              >
                <span
                  style={{
                    display: "flex",
                    fontSize: 36,
                    fontWeight: 700,
                    color: OG_COLORS.paper,
                    textAlign: "center",
                    lineHeight: 1.3,
                  }}
                >
                  {cycleInsight.stageLabel}
                </span>
                <span style={{ display: "flex", fontSize: 18, color: OG_COLORS.accentLight, letterSpacing: 2, marginTop: 12 }}>
                  {cycleInsight.tier === "fact" ? "FACT" : "AI推測"}
                </span>
              </div>
            )
          )}
        </div>

        <Footer right="相場推移・ショップ別価格・買い時判定" />
      </div>
    ),
    { ...size }
  );
}
