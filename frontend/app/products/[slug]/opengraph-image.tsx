import { ImageResponse } from "next/og";

import { getProduct } from "@/lib/api";
import { verdictInfo } from "@/lib/buySignal";
import { getFallbackValueScore } from "@/lib/fallbackScore";
import { getModelCycleInsight } from "@/lib/modelCycle";
import {
  BrandMark,
  CtaPill,
  Footer,
  HookChip,
  OG_API_TIMEOUT_MS,
  OG_SIZE,
  POP,
  PercentBadge,
  PhotoTile,
  dropWhen,
  fetchImageDataUri,
  findRecentDrop,
  ogFonts,
  productShareFacts,
  truncate,
  withTimeout,
  yen,
} from "@/lib/og";

export const alt = "PAR. 価格推移と買い時判定";
export const size = OG_SIZE;
export const contentType = "image/png";

// 2026-11-12 (社長指示): "値下がり速報" look for the card X shows under a
// posted product link - one huge yellow number, a red percent sticker on
// the photo and a button-shaped call to action. Every number is still a
// recorded fact (see lib/og.tsx rule 2).

const root = {
  width: "100%",
  height: "100%",
  display: "flex",
  background: POP.bg,
  fontFamily: "PAR",
} as const;

// Big-number font size so "¥33,000" + "ダウン" fit the ~690px text column.
function bigSize(text: string): number {
  return text.length <= 6 ? 136 : text.length === 7 ? 118 : 100;
}

function Arrow() {
  return (
    <svg width="44" height="36" viewBox="0 0 44 36">
      <path d="M2 18 H34 M22 5 L36 18 L22 31" stroke={POP.yellow} strokeWidth="6" fill="none" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default async function Image({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const product = await withTimeout(getProduct(slug, { signal: AbortSignal.timeout(OG_API_TIMEOUT_MS) }));

  if (!product) {
    // Backend asleep/unreachable or unknown slug: still a branded card,
    // never an error (an error is what X renders as a grey placeholder).
    const cta = "いまの値段を見る";
    const footerRight = "価格推移と買い時判定を毎日更新";
    const fonts = await ogFonts(["買い時チェック", "そのギア、今が買い時？", cta, footerRight]);
    return new ImageResponse(
      (
        <div style={{ ...root, flexDirection: "column", justifyContent: "space-between", padding: "48px 60px 40px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <BrandMark size={36} />
            <HookChip text="買い時チェック" />
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 28 }}>
            <span style={{ display: "flex", fontSize: 96, fontWeight: 900, color: POP.white, lineHeight: 1.15 }}>そのギア、</span>
            <span style={{ display: "flex", fontSize: 96, fontWeight: 900, color: POP.yellow, lineHeight: 1.15, marginTop: -28 }}>
              今が買い時？
            </span>
            <div style={{ display: "flex" }}>
              <CtaPill text={cta} />
            </div>
          </div>
          <Footer right={footerRight} />
        </div>
      ),
      { ...size, fonts }
    );
  }

  const facts = productShareFacts(product);
  const photo = await fetchImageDataUri(product.image_url);
  const drop = findRecentDrop(product);
  const name = truncate(`${product.brand} ${product.name}`, 30);

  // A recent real price drop: the drop itself is the headline.
  if (drop) {
    const big = yen(drop.yenDown);
    const when = `${dropWhen(drop)}の記録`;
    const tease = `${drop.stableDays}日間 ${yen(drop.before)} のままだったのに…`;
    const cta = "値動きグラフを見る";
    const fonts = await ogFonts(["値下がり速報", when, big, "ダウン", name, tease, cta, yen(drop.before), yen(drop.after)]);
    return new ImageResponse(
      (
        <div style={root}>
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              justifyContent: "space-between",
              flex: 1,
              padding: "42px 0 38px 56px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
              <HookChip text="値下がり速報" />
              <span style={{ display: "flex", fontSize: 28, fontWeight: 900, color: POP.white }}>{when}</span>
            </div>

            <div style={{ display: "flex", flexDirection: "column" }}>
              <div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
                <span style={{ display: "flex", fontSize: bigSize(big), fontWeight: 900, color: POP.yellow, lineHeight: 1.05 }}>
                  {big}
                </span>
                <span style={{ display: "flex", fontSize: 56, fontWeight: 900, color: POP.white }}>ダウン</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 18, marginTop: 6 }}>
                <span style={{ display: "flex", fontSize: 42, fontWeight: 500, color: POP.gray, textDecoration: "line-through" }}>
                  {yen(drop.before)}
                </span>
                <Arrow />
                <span style={{ display: "flex", fontSize: 70, fontWeight: 900, color: POP.white, lineHeight: 1.1 }}>
                  {yen(drop.after)}
                </span>
              </div>
              <span style={{ display: "flex", fontSize: 28, fontWeight: 900, color: POP.yellow, marginTop: 14 }}>{tease}</span>
              <span style={{ display: "flex", fontSize: 24, fontWeight: 500, color: POP.gray, marginTop: 6 }}>{name}</span>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
              <CtaPill text={cta} />
              <span style={{ display: "flex", fontSize: 22, fontWeight: 500, color: POP.gray }}>par-gear.com</span>
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", width: 470 }}>
            {photo ? (
              <PhotoTile src={photo} size={370} badge={`-${drop.percentDown}%`} />
            ) : (
              <PercentBadge text={`-${drop.percentDown}%`} size={300} />
            )}
          </div>
        </div>
      ),
      { ...size, fonts }
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
      ? `定価より ${yen(facts.savingsYen)} 安い`
      : facts.hasReliableTrend && product.price_change_percent !== null && product.price_change_percent !== 0
        ? `30日平均比 ${product.price_change_percent > 0 ? "+" : ""}${product.price_change_percent}%`
        : null;

  // Red sticker only for a real discount: vs MSRP, else vs the 30-day average.
  const badge =
    facts.savingsPercent !== null && facts.savingsPercent >= 5
      ? { text: `-${facts.savingsPercent}%`, caption: "定価比" }
      : facts.hasReliableTrend && product.price_change_percent !== null && product.price_change_percent <= -5
        ? { text: `${Math.round(product.price_change_percent)}%`, caption: "30日平均比" }
        : null;

  const chip = facts.hook ?? "買い時チェック";
  const price = yen(product.current_price);
  const cta = "今が買い時か見る";
  const fonts = await ogFonts([chip, name, price, savingsLine, signalLabel, cta, "定価比30日平均比"]);

  return new ImageResponse(
    (
      <div style={root}>
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
            flex: 1,
            padding: "42px 0 38px 56px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
            <HookChip text={chip} />
          </div>

          <div style={{ display: "flex", flexDirection: "column" }}>
            <span style={{ display: "flex", fontSize: 30, fontWeight: 900, color: POP.white, lineHeight: 1.3 }}>{name}</span>
            <span style={{ display: "flex", fontSize: bigSize(price) + 8, fontWeight: 900, color: POP.yellow, lineHeight: 1.1, marginTop: 6 }}>
              {price}
            </span>
            {savingsLine && (
              <span style={{ display: "flex", fontSize: 40, fontWeight: 900, color: POP.white, marginTop: 4 }}>{savingsLine}</span>
            )}
            {signalLabel && (
              <span style={{ display: "flex", fontSize: 24, fontWeight: 500, color: POP.gray, marginTop: 10 }}>{signalLabel}</span>
            )}
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
            <CtaPill text={cta} />
            <span style={{ display: "flex", fontSize: 22, fontWeight: 500, color: POP.gray }}>par-gear.com</span>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", width: 470 }}>
          {photo ? (
            <PhotoTile src={photo} size={370} badge={badge?.text} badgeCaption={badge?.caption} />
          ) : badge ? (
            <PercentBadge text={badge.text} size={300} caption={badge.caption} />
          ) : null}
        </div>
      </div>
    ),
    { ...size, fonts }
  );
}
