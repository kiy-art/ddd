import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import AiBuySignal from "@/components/AiBuySignal";
import CategoryIcon from "@/components/CategoryIcon";
import CompareButton from "@/components/CompareButton";
import CompareStrip from "@/components/CompareStrip";
import DataSourceNote from "@/components/DataSourceNote";
import FadeIn from "@/components/FadeIn";
import FavoriteButton from "@/components/FavoriteButton";
import MonthlyTrendChart from "@/components/MonthlyTrendChart";
import PriceAlertForm from "@/components/PriceAlertForm";
import PriceForecast from "@/components/PriceForecast";
import PriceHistoryChartPanel from "@/components/PriceHistoryChartPanel";
import PriceRangeBar from "@/components/PriceRangeBar";
import PriceTimeline from "@/components/PriceTimeline";
import ProductFAQ from "@/components/ProductFAQ";
import SafeProductImage from "@/components/SafeProductImage";
import StoreComparisonTable from "@/components/StoreComparisonTable";
import TrackedCta from "@/components/TrackedCta";
import TrackViewed from "@/components/TrackViewed";
import { CATEGORY_LABELS, Product, getCategoryProducts, getProduct } from "@/lib/api";
import { getPopularityBadge, getPositioningFacts, getProductBadge } from "@/lib/badges";
import { getFallbackValueScore } from "@/lib/fallbackScore";
import { MODEL_CYCLE_DISCLAIMER, MODEL_CYCLE_FACT_NOTE, getModelCycleInsight } from "@/lib/modelCycle";

export const revalidate = 0;

type Params = { slug: string };

// Below this many days of accumulated price history, a "30-day average" or
// "all-time low" claim would overstate how much we actually know - show an
// honest "still accumulating data" state instead (see spec: never present
// thin data as if it were a stable trend).
const THIN_DATA_DAYS = 7;

const VERDICT_HEADLINE: Record<string, string> = {
  strong_buy: "今は「買い時」です",
  buy: "今は「買い時」です",
  neutral: "今は「様子見」が妥当です",
  not_buy: "今は「買い時」ではありません",
  insufficient_data: "価格分析の準備中です",
};

// The backend already rejects a fetched price outside 0.5x-2.0x of the
// known average before it's ever saved (see pipeline.py), so nothing in
// the DB should be a flat-out mismatch. This is a second, tighter
// threshold purely for display: even a *legitimate* drop this large is
// unusual enough that a user should double-check before trusting it,
// rather than the page presenting it as an uncomplicated "great deal".
const CAUTION_DISCOUNT_PERCENT = -40;

function yen(value: number | null): string {
  if (value === null) return "-";
  return `¥${value.toLocaleString("ja-JP")}`;
}

function ctaLabel(url: string): string {
  try {
    const host = new URL(url).hostname;
    if (host.includes("rakuten.co.jp")) return "楽天市場で価格を見る";
    if (host.includes("amazon.co.jp") || host.includes("amazon.com")) return "Amazonで価格を見る";
  } catch {
    // fall through to the generic label below
  }
  return "販売ページで価格を見る";
}

// Deterministic, keyword-targeted <title>/meta description/OGP/JSON-LD text
// built purely from real facts (price, lowest price) - used unconditionally,
// never swapped out for product.ai_title/ai_summary. Those are Claude-
// generated for on-page reading (shown separately further down this page)
// and were never written with search intent in mind ("最安値", "買い時判定",
// "安くなる時期"), so preferring them for metadata would silently make every
// AI-enriched product's SEO worse than a brand-new, not-yet-processed one's.
function seoTitle(product: Product): string {
  // No manual "- PAR." suffix: the root layout's title.template
  // ("%s | PAR.") already appends the brand to every page title, so
  // adding it here too would show it twice in the tab title/SERP snippet.
  const modelPart = product.model_number ? ` ${product.model_number}` : "";
  return `${product.brand} ${product.name}${modelPart}の最安値・買い時判定｜価格推移とAI予測`;
}

function seoDescription(product: Product): string {
  const lowestPart = product.lowest_price !== null ? `（過去最安値 ${yen(product.lowest_price)}）` : "";
  const currentPart = product.current_price !== null ? yen(product.current_price) : "価格情報";
  return `${product.brand} ${product.name}の価格推移${lowestPart}をもとに、今が買い時かをAIが分析。値下がりしやすい時期の目安も掲載しています。現在価格は${currentPart}です。`;
}

// A plain helper (not called directly in the component body) so the
// Date.now() fallback doesn't trip the "components must be pure" lint rule
// - this page re-renders live on every request anyway (`revalidate = 0`),
// so the impurity is intentional and harmless, just not allowed inline.
function computePriceValidUntil(lastPriceUpdatedAt: string | null): string {
  const base = lastPriceUpdatedAt ? new Date(lastPriceUpdatedAt).getTime() : Date.now();
  return new Date(base + 7 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
}

async function loadProduct(slug: string) {
  try {
    return await getProduct(slug);
  } catch {
    return null;
  }
}

export async function generateMetadata({ params }: { params: Promise<Params> }): Promise<Metadata> {
  const { slug } = await params;
  const product = await loadProduct(slug);
  if (!product) return {};

  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";
  const url = `${siteUrl}/products/${product.slug}`;
  const title = seoTitle(product);
  const description = seoDescription(product);
  // openGraph/twitter titles aren't run through the root layout's
  // title.template ("%s | PAR.") the way the <title> field is, so the
  // brand needs to be appended explicitly here to match.
  const ogTitle = `${title} - PAR.`;

  return {
    title,
    description,
    alternates: { canonical: url },
    openGraph: {
      type: "website",
      url,
      title: ogTitle,
      description,
    },
    twitter: {
      card: "summary_large_image",
      title: ogTitle,
      description,
    },
  };
}

export default async function ProductPage({ params }: { params: Promise<Params> }) {
  const { slug } = await params;
  const product = await loadProduct(slug);
  if (!product) notFound();

  const hasReliableTrend = product.buy_score !== "insufficient_data" && product.history_span_days >= THIN_DATA_DAYS;
  const fallbackScore = hasReliableTrend
    ? null
    : getFallbackValueScore({ msrp: product.msrp, current_price: product.current_price, release_date: product.release_date });
  // Only consulted once the MSRP-based fallback above has nothing to say
  // (no msrp on file) - a weaker, text-only read from release date/
  // generation status, never overriding a real price-based figure.
  const cycleInsight =
    hasReliableTrend || fallbackScore
      ? null
      : getModelCycleInsight({ release_date: product.release_date, is_current_generation: product.is_current_generation });
  const badge = getProductBadge(product);
  const popularityBadge = getPopularityBadge(product);
  const positioningFacts = getPositioningFacts(product);
  const msrpPct =
    product.msrp !== null && product.current_price !== null
      ? Math.round(((product.current_price - product.msrp) / product.msrp) * 1000) / 10
      : null;
  const needsPriceCaution =
    hasReliableTrend &&
    product.price_change_percent !== null &&
    product.price_change_percent <= CAUTION_DISCOUNT_PERCENT;

  // The API only ever sends us the all-time low (lowest_price) and 30-day
  // average (average_price), not an all-time high - but the full
  // price_history array is already on the page, so the high is a real
  // derived value from real data, not a guess (see PriceRangeBar).
  const highestPrice =
    product.price_history.length > 0
      ? Math.max(...product.price_history.map((h) => h.price), product.current_price ?? 0)
      : product.current_price;
  const hasFullRange =
    hasReliableTrend &&
    product.lowest_price !== null &&
    product.average_price !== null &&
    highestPrice !== null &&
    product.current_price !== null;

  const lastPriceUpdatedAt =
    product.price_history.length > 0 ? product.price_history[product.price_history.length - 1].recorded_at : null;

  let categoryProducts: Product[] = [];
  try {
    categoryProducts = await getCategoryProducts(product.category);
  } catch {
    categoryProducts = [];
  }
  const compareProducts = [
    product,
    ...categoryProducts
      .filter((p) => p.id !== product.id && p.buy_signal_score !== null)
      .sort((a, b) => (b.buy_signal_score ?? 0) - (a.buy_signal_score ?? 0))
      .slice(0, 2),
  ];

  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";

  // Google recommends priceValidUntil on Offer/AggregateOffer for the price
  // to be eligible for rich results. This page is fully dynamic (no cache,
  // see `revalidate = 0` above) and re-renders live from the DB on every
  // crawl, so a short, honest window - "current as of the last recorded
  // price fetch, good for about a week" - matches this site's own daily
  // refresh cadence rather than overclaiming a price that far outlives it.
  const priceValidUntil = computePriceValidUntil(lastPriceUpdatedAt);

  // Two independent, real price sources (Rakuten via current_price, Yahoo!
  // via yahoo_price - see StoreComparisonTable) become an AggregateOffer
  // when both are known, matching Google's guidance for a product sold
  // through multiple listings; a single known price stays a plain Offer.
  const offerSources: { price: number; url: string }[] = [];
  if (product.current_price !== null) {
    offerSources.push({
      price: product.current_price,
      url: product.affiliate_url || product.product_url || `${siteUrl}/products/${product.slug}`,
    });
  }
  if (product.yahoo_price !== null && product.yahoo_url) {
    offerSources.push({ price: product.yahoo_price, url: product.yahoo_url });
  }

  const offers =
    offerSources.length === 1
      ? {
          "@type": "Offer",
          priceCurrency: "JPY",
          price: offerSources[0].price,
          availability: "https://schema.org/InStock",
          url: offerSources[0].url,
          priceValidUntil,
        }
      : offerSources.length >= 2
        ? {
            "@type": "AggregateOffer",
            priceCurrency: "JPY",
            lowPrice: Math.min(...offerSources.map((o) => o.price)),
            highPrice: Math.max(...offerSources.map((o) => o.price)),
            offerCount: offerSources.length,
            priceValidUntil,
            offers: offerSources.map((o) => ({
              "@type": "Offer",
              priceCurrency: "JPY",
              price: o.price,
              availability: "https://schema.org/InStock",
              url: o.url,
            })),
          }
        : null;

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Product",
    name: product.name,
    description: seoDescription(product),
    sku: product.model_number || String(product.id),
    brand: { "@type": "Brand", name: product.brand },
    ...(product.model_number ? { mpn: product.model_number } : {}),
    ...(product.image_url ? { image: [product.image_url] } : {}),
    url: `${siteUrl}/products/${product.slug}`,
    ...(offers ? { offers } : {}),
  };

  const breadcrumbJsonLd = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "PAR.", item: siteUrl },
      {
        "@type": "ListItem",
        position: 2,
        name: CATEGORY_LABELS[product.category] ?? product.category,
        item: `${siteUrl}/category/${product.category}`,
      },
      { "@type": "ListItem", position: 3, name: product.name, item: `${siteUrl}/products/${product.slug}` },
    ],
  };

  return (
    <article>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbJsonLd) }} />

      <div className="border-b border-border bg-card">
        <div className="mx-auto max-w-7xl px-6 py-8">
          <Link href={`/category/${product.category}`} className="text-xs font-medium uppercase tracking-widest text-foreground/40 hover:text-brand">
            ← {CATEGORY_LABELS[product.category] ?? product.category}
          </Link>
        </div>
      </div>

      <div className="mx-auto max-w-7xl px-6 py-12 sm:py-16">
        <div className="grid grid-cols-1 gap-12 lg:grid-cols-2 lg:gap-16">
          <FadeIn className="flex flex-col gap-2">
            <div className="relative aspect-square w-full overflow-hidden rounded-2xl border border-border bg-card">
              {product.image_url ? (
                <SafeProductImage
                  src={product.image_url}
                  alt={product.name}
                  category={product.category}
                  className="object-contain p-10"
                />
              ) : (
                <CategoryIcon category={product.category} />
              )}
            </div>
            {product.image_url?.includes("rakuten.co.jp") && (
              <p className="text-right text-[11px] text-foreground/35">画像提供: 楽天市場</p>
            )}
          </FadeIn>

          <FadeIn delay={100} className="flex flex-col gap-6">
            <TrackViewed slug={product.slug} />
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="flex items-center gap-2">
                  <Link
                    href={`/brand/${encodeURIComponent(product.brand)}`}
                    className="text-xs font-medium uppercase tracking-widest text-foreground/40 hover:text-brand"
                  >
                    {product.brand}
                  </Link>
                  {popularityBadge && (
                    <span className="rounded-full bg-brand px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-widest text-white">
                      {popularityBadge.label}
                    </span>
                  )}
                  {badge && (
                    <span
                      className={`rounded-full px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-widest ${
                        badge.tone === "strong" ? "bg-brand text-white" : "bg-ink text-white"
                      }`}
                    >
                      {badge.label}
                    </span>
                  )}
                </div>
                <h1 className="mt-2 font-display text-3xl font-semibold leading-tight text-foreground sm:text-4xl">
                  {product.name}
                </h1>
                {product.release_date && (
                  <p className="mt-1 text-xs text-foreground/40">
                    発売日 {new Date(product.release_date).toLocaleDateString("ja-JP")}
                  </p>
                )}
                {positioningFacts.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {positioningFacts.map((fact) => (
                      <span
                        key={fact.label}
                        className="rounded-full border border-border bg-background px-2.5 py-1 text-[11px] font-medium text-foreground/60"
                      >
                        {fact.label}
                      </span>
                    ))}
                  </div>
                )}
              </div>
              <div className="flex shrink-0 items-center gap-2">
                <CompareButton slug={product.slug} />
                <FavoriteButton
                  slug={product.slug}
                  className="rounded-full border border-border p-3 text-foreground/50 transition-colors hover:text-brand"
                />
              </div>
            </div>

            <div className="flex items-center gap-6 rounded-2xl border border-border bg-card p-6">
              <AiBuySignal
                buyScore={product.buy_score}
                buySignalScore={product.buy_signal_score}
                historySpanDays={product.history_span_days}
                msrp={product.msrp}
                currentPrice={product.current_price}
                releaseDate={product.release_date}
                size="lg"
              />
              <div className="flex flex-col gap-1 border-l border-border pl-6">
                <div className="flex items-center gap-2">
                  <span className="rounded-full bg-emerald-600 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-widest text-white">
                    FACT
                  </span>
                  <span className="text-xs text-foreground/40">現在価格</span>
                </div>
                <span className="font-display text-4xl font-semibold text-foreground">
                  {yen(product.current_price)}
                </span>
                {msrpPct !== null && (
                  <span className={`text-sm font-semibold ${msrpPct < 0 ? "text-brand dark:text-brand-light" : "text-foreground/50"}`}>
                    {msrpPct > 0 ? "+" : ""}
                    {msrpPct}% 定価より
                  </span>
                )}
                {hasReliableTrend && product.price_change_percent !== null ? (
                  <span className={msrpPct !== null ? "text-xs text-foreground/40" : "text-sm font-semibold " + (product.price_change_percent < 0 ? "text-brand dark:text-brand-light" : "text-foreground/50")}>
                    {product.price_change_percent > 0 ? "+" : ""}
                    {product.price_change_percent}% vs 30日平均
                  </span>
                ) : (
                  msrpPct === null && (
                    <span className="text-sm font-medium text-foreground/40">
                      {product.history_span_days > 0 ? "価格分析準備中です" : "登録されたばかりの商品です"}
                    </span>
                  )
                )}
              </div>
            </div>

            <div className="rounded-2xl border border-border bg-background p-6">
              <span className="text-xs font-medium uppercase tracking-widest text-foreground/40">今買うべき？</span>
              <p className="mt-2 font-display text-xl font-semibold text-foreground">
                {hasReliableTrend
                  ? VERDICT_HEADLINE[product.buy_score] ?? VERDICT_HEADLINE.neutral
                  : fallbackScore
                    ? fallbackScore.msrpPct < 0
                      ? `定価より${fallbackScore.msrpPct}%（参考値）`
                      : "定価とほぼ同水準です（参考値）"
                    : cycleInsight
                      ? cycleInsight.stageLabel
                      : VERDICT_HEADLINE.insufficient_data}
              </p>
              <p className="mt-2 text-sm leading-relaxed text-foreground/60">
                {hasReliableTrend
                  ? product.buy_reason
                  : fallbackScore
                    ? `メーカー希望小売価格（定価）と比べて${fallbackScore.msrpPct > 0 ? "+" : ""}${fallbackScore.msrpPct}%の価格です。価格推移データが蓄積されるまでの参考情報としてご覧ください。`
                    : cycleInsight
                      ? cycleInsight.message
                      : product.history_span_days > 0
                        ? "価格分析の準備中です。もう少しデータが揃い次第、買い時かどうかをお伝えします。"
                        : "登録されたばかりの商品です。判定が可能になり次第お伝えします。"}
              </p>
              {!hasReliableTrend && fallbackScore && (
                <p
                  className="mt-3 rounded-xl border border-dashed px-3 py-2 text-xs leading-relaxed text-foreground/50"
                  style={{ borderColor: "var(--accent-dark)" }}
                >
                  ※価格推移データがまだ少ないため、メーカー希望小売価格との比較に基づく参考値です
                </p>
              )}
              {!hasReliableTrend && !fallbackScore && cycleInsight && (
                <p
                  className="mt-3 rounded-xl border border-dashed px-3 py-2 text-xs leading-relaxed text-foreground/50"
                  style={{ borderColor: cycleInsight.tier === "fact" ? "var(--ink)" : "var(--accent-dark)" }}
                >
                  {cycleInsight.tier === "fact" ? MODEL_CYCLE_FACT_NOTE : MODEL_CYCLE_DISCLAIMER}
                </p>
              )}
              {needsPriceCaution && (
                <p className="mt-3 rounded-xl border border-border bg-card px-3 py-2 text-xs leading-relaxed text-foreground/50">
                  ⚠ 価格要確認：通常価格帯から大きく外れた値下がりです。掲載元での価格反映のタイムラグや、
                  商品の取り違えなどの可能性もゼロではありません。購入前に実際の販売ページで価格をご確認ください。
                </p>
              )}
            </div>

            {hasFullRange && (
              <PriceRangeBar
                low={product.lowest_price!}
                average={product.average_price!}
                high={highestPrice!}
                current={product.current_price!}
              />
            )}

            <dl className={`grid gap-4 text-xs text-foreground/45 ${product.msrp !== null ? "grid-cols-2 sm:grid-cols-4" : "grid-cols-3"}`}>
              {product.msrp !== null && (
                <div>
                  <dt>メーカー希望小売価格</dt>
                  <dd className="mt-1 font-display text-base font-medium text-foreground">{yen(product.msrp)}</dd>
                </div>
              )}
              <div>
                <dt>過去30日平均</dt>
                {hasReliableTrend ? (
                  <dd className="mt-1 font-display text-base font-medium text-foreground">
                    {yen(product.average_price)}
                  </dd>
                ) : (
                  <dd className="mt-1 text-[11px] font-medium leading-snug text-foreground/40">分析準備中</dd>
                )}
              </div>
              <div>
                <dt>過去最安値</dt>
                <dd className="mt-1 font-display text-base font-medium text-foreground">{yen(product.lowest_price)}</dd>
              </div>
              <div>
                <dt>前回価格</dt>
                <dd className="mt-1 font-display text-base font-medium text-foreground">{yen(product.previous_price)}</dd>
              </div>
            </dl>

            <div className="flex flex-col gap-2 rounded-2xl border border-border bg-card p-5">
              <span className="text-xs text-foreground/45">現在価格</span>
              <span className="font-display text-2xl font-semibold text-foreground">{yen(product.current_price)}</span>
              <div className="mt-2 flex flex-col gap-2 sm:flex-row">
                {product.affiliate_url && (
                  <TrackedCta
                    href={product.affiliate_url}
                    target="_blank"
                    rel="noopener noreferrer sponsored"
                    className="flex-1 rounded-full bg-brand px-6 py-4 text-center text-sm font-semibold text-white transition-transform hover:scale-[1.02]"
                    event="cta_click"
                    params={{
                      product_id: product.id,
                      product_slug: product.slug,
                      product_name: product.name,
                      cta_type: "affiliate",
                      buy_score: product.buy_score,
                    }}
                  >
                    {ctaLabel(product.affiliate_url)}
                  </TrackedCta>
                )}
                {product.product_url && (
                  <TrackedCta
                    href={product.product_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex-1 rounded-full border border-border px-6 py-4 text-center text-sm font-semibold text-foreground/80 transition-colors hover:bg-background"
                    event="cta_click"
                    params={{
                      product_id: product.id,
                      product_slug: product.slug,
                      product_name: product.name,
                      cta_type: "official",
                      buy_score: product.buy_score,
                    }}
                  >
                    メーカー商品ページを見る
                  </TrackedCta>
                )}
              </div>
              <a href="#store-comparison" className="text-center text-xs font-semibold text-brand hover:underline">
                他の販売価格を比較する ↓
              </a>
              {product.affiliate_url && (
                <p className="text-xs text-foreground/35">
                  ※広告・PRを含みます。上記リンクにはアフィリエイトリンクが含まれる場合があり、リンク経由の購入により当サイトが紹介料を受け取ることがあります。価格・在庫は変動するため、購入前に販売元サイトでご確認ください。
                </p>
              )}
            </div>
          </FadeIn>
        </div>

        {compareProducts.length >= 2 && (
          <FadeIn className="mt-10">
            <span className="text-xs font-medium uppercase tracking-[0.3em] text-accent">Related</span>
            <h2 className="mt-2 font-display text-2xl font-semibold text-foreground">関連商品・同じカテゴリの候補と比較</h2>
            <div className="mt-6">
              <CompareStrip products={compareProducts} currentId={product.id} />
            </div>
          </FadeIn>
        )}

        <FadeIn className="mt-16 rounded-2xl border border-border bg-card p-6 sm:p-10">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium uppercase tracking-[0.3em] text-accent">Price History</span>
            <span className="rounded-full bg-emerald-600 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-widest text-white">
              FACT
            </span>
          </div>
          <h2 className="mt-2 font-display text-2xl font-semibold text-foreground">価格推移チャート</h2>
          <div className="mt-8">
            <PriceHistoryChartPanel
              history={product.price_history}
              forecast={
                product.forecast_center_price !== null &&
                product.forecast_low_price !== null &&
                product.forecast_high_price !== null &&
                product.forecast_target_date !== null
                  ? {
                      centerPrice: product.forecast_center_price,
                      lowPrice: product.forecast_low_price,
                      highPrice: product.forecast_high_price,
                      targetDate: product.forecast_target_date,
                    }
                  : null
              }
              referenceLines={[
                ...(product.lowest_price !== null ? [{ label: "過去最安", value: product.lowest_price }] : []),
                ...(hasReliableTrend && product.average_price !== null
                  ? [{ label: "過去平均", value: product.average_price }]
                  : []),
              ]}
            />
          </div>
        </FadeIn>

        <FadeIn className="mt-10">
          <PriceForecast product={product} />
        </FadeIn>

        <FadeIn className="mt-10 rounded-2xl border border-border bg-card p-6 sm:p-10">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium uppercase tracking-[0.3em] text-accent">Long-Term Trend</span>
            <span className="rounded-full bg-emerald-600 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-widest text-white">
              FACT
            </span>
          </div>
          <h2 className="mt-2 font-display text-2xl font-semibold text-foreground">長期価格推移（月次・最大3年）</h2>
          <div className="mt-8">
            <MonthlyTrendChart history={product.price_history} />
          </div>
        </FadeIn>

        <FadeIn className="mt-10">
          <PriceTimeline product={product} />
        </FadeIn>

        <FadeIn id="store-comparison" className="mt-10 scroll-mt-20">
          <StoreComparisonTable product={product} lastUpdatedAt={lastPriceUpdatedAt} />
        </FadeIn>

        <FadeIn className="mt-10">
          <PriceAlertForm slug={product.slug} currentPrice={product.current_price} />
        </FadeIn>

        {product.ai_summary && product.ai_summary !== product.buy_reason && (
          <FadeIn className="mt-10 rounded-2xl border border-border bg-card p-6 sm:p-10">
            <span className="text-xs font-medium uppercase tracking-[0.3em] text-accent">More Detail</span>
            <h2 className="mt-2 font-display text-2xl font-semibold text-foreground">価格データからわかること</h2>
            <div className="mt-5 flex flex-col gap-4 text-sm leading-relaxed text-foreground/70">
              <p>{product.ai_summary}</p>
            </div>
          </FadeIn>
        )}

        {product.ai_caution && (
          <p className="mt-8 rounded-xl border border-border bg-card px-4 py-3 text-xs text-foreground/45">
            ⚠ {product.ai_caution}
          </p>
        )}

        <FadeIn className="mt-10">
          <ProductFAQ product={product} />
        </FadeIn>

        <FadeIn className="mt-10">
          <DataSourceNote />
        </FadeIn>
      </div>
    </article>
  );
}
