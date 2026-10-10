import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import AiBuySignal from "@/components/AiBuySignal";
import CtaArrow from "@/components/CtaArrow";
import ScoreExplanation from "@/components/ScoreExplanation";
import CompareButton from "@/components/CompareButton";
import CompareStrip from "@/components/CompareStrip";
import ConsumablesCorner from "@/components/ConsumablesCorner";
import DataSourceNote from "@/components/DataSourceNote";
import FadeIn from "@/components/FadeIn";
import FavoriteButton from "@/components/FavoriteButton";
import MonthlyTrendChart from "@/components/MonthlyTrendChart";
import PriceAlertForm, { type AlertSuggestion } from "@/components/PriceAlertForm";
import PriceForecast from "@/components/PriceForecast";
import PriceHistoryChartPanel from "@/components/PriceHistoryChartPanel";
import PriceRangeBar from "@/components/PriceRangeBar";
import PriceTimeline from "@/components/PriceTimeline";
import ProductOverview from "@/components/ProductOverview";
import ProductFAQ from "@/components/ProductFAQ";
import SafeProductImage from "@/components/SafeProductImage";
import StickyBuyBar from "@/components/StickyBuyBar";
import StoreComparisonTable from "@/components/StoreComparisonTable";
import TrackedCta from "@/components/TrackedCta";
import TrackViewed from "@/components/TrackViewed";
import { CATEGORY_LABELS, Product, ProductDetail, getCategoryProducts, getProduct, getSiteStats } from "@/lib/api";
import { getPopularityBadge, getPositioningFacts, getProductBadge } from "@/lib/badges";
import { getFallbackValueScore } from "@/lib/fallbackScore";
import { MODEL_CYCLE_DISCLAIMER, MODEL_CYCLE_FACT_NOTE, getModelCycleInsight } from "@/lib/modelCycle";
import { normalizeImageUrl } from "@/lib/imageUrl";
import { nearestRivals, pairHref } from "@/lib/comparePairs";
import { buildProductJsonLd } from "@/lib/productJsonLd";
import { productSeoDescription, productSeoTitle } from "@/lib/productSeo";
import { getLowestOffer, getShopOffers } from "@/lib/shopOffers";
import { SHOP_MARKS, buildShopBoard, staleLabel } from "@/lib/shopRows";
import { SITE_URL } from "@/lib/siteUrl";

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

// Deterministic, keyword-targeted <title>/meta description/OGP/JSON-LD text
// built purely from real facts (price, lowest price) - used unconditionally,
// never swapped out for product.ai_title/ai_summary. Those are Claude-
// generated for on-page reading (shown separately further down this page)
// and were never written with search intent in mind ("最安値", "買い時判定",
// "安くなる時期"), so preferring them for metadata would silently make every
// AI-enriched product's SEO worse than a brand-new, not-yet-processed one's.
// STEP69: one-tap target prices for the alert form - only real numbers
// from this page, each labeled with its source, and only ones below
// today's price (an alert at or above it would fire at once).
function priceAlertSuggestions(product: ProductDetail): AlertSuggestion[] {
  const current = product.current_price;
  if (current === null) return [];
  const out: AlertSuggestion[] = [];
  const add = (label: string, price: number | null) => {
    if (price === null || price <= 0 || price >= current) return;
    const rounded = Math.floor(price / 100) * 100;
    if (rounded > 0 && !out.some((s) => s.price === rounded)) out.push({ label, price: rounded });
  };
  add("今より5%安い", current * 0.95);
  add("過去最安値", product.lowest_price);
  add("予測レンジ下限", product.forecast_low_price);
  return out.slice(0, 3);
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

  const siteUrl = SITE_URL;
  const url = `${siteUrl}/products/${product.slug}`;
  // STEP68: the full title already ends with the site name, so it's set
  // as `absolute` - the root layout's title.template ("%s | PAR.") would
  // otherwise add the brand a second time.
  const title = productSeoTitle(product);
  const description = productSeoDescription(product);
  const ogTitle = title;

  return {
    title: { absolute: title },
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
  const lastPriceUpdatedAt =
    product.price_history.length > 0 ? product.price_history[product.price_history.length - 1].recorded_at : null;
  // STEP56: the lowest recent price across the shops that have one
  // (Rakuten / Yahoo!) - shown at the top and used for the main buy button.
  // With only one shop priced, this is just that shop's price.
  const shopOffers = getShopOffers(product, lastPriceUpdatedAt);
  const lowestOffer = getLowestOffer(shopOffers);
  const comparedOffers = shopOffers.length >= 2;
  const displayPrice = lowestOffer?.price ?? product.current_price;
  const otherOffers = shopOffers.filter((offer) => offer !== lowestOffer);
  // The history stats (30-day average, record low, previous price) are
  // Rakuten's own series - say so when a cheaper Yahoo! price is on top.
  const shopBoard = buildShopBoard(product, lastPriceUpdatedAt);
  // STEP74: rows come fresh-first (lib/shopRows.ts), so with no comparison
  // the main button is the shop with the most recent price - never a shop
  // whose last price is days old just because that old number was lower.
  const primaryShop =
    shopBoard.rows.find((row) => row.isLowest) ?? shopBoard.rows.find((row) => row.kind === "price") ?? null;
  const secondaryShops = shopBoard.rows.filter((row) => row !== primaryShop && row.kind !== "official");
  const officialShop = shopBoard.rows.find((row) => row.kind === "official") ?? null;
  // STEP65: the pinned buy bar - the buy box's main shop, or (no fetched
  // price) the first shop search link, so there's always somewhere to go.
  const stickyShop = primaryShop ?? secondaryShops[0] ?? null;
  // Only the price the page itself shows at the top (a fresh offer, or
  // Rakuten's current price) - never a stale one from another shop's row.
  const stickyPrice =
    stickyShop === null
      ? null
      : lowestOffer
        ? stickyShop.key === lowestOffer.shop
          ? lowestOffer.price
          : null
        : stickyShop.key === "rakuten"
          ? product.current_price
          : null;
  const rakutenSeriesSuffix = lowestOffer?.shop === "yahoo" ? "（楽天）" : "";
  const msrpPct =
    product.msrp !== null && displayPrice !== null
      ? Math.round(((displayPrice - product.msrp) / product.msrp) * 1000) / 10
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

  let categoryProducts: Product[] = [];
  // STEP69: price alerts are only offered when the email can really reach
  // a visitor (backend email.can_email_visitors).
  const statsPromise = getSiteStats().catch(() => null);
  try {
    categoryProducts = await getCategoryProducts(product.category, undefined, 50); // candidates for related items only
  } catch {
    categoryProducts = [];
  }
  const alertsEnabled = (await statsPromise)?.price_alerts_enabled === true;
  // "Not a buy today" - the visitor most likely to leave without clicking.
  const waitVerdict = !(hasReliableTrend && (product.buy_score === "buy" || product.buy_score === "strong_buy"));
  const showInlineAlert = alertsEnabled && waitVerdict && product.current_price !== null;
  const alertSuggestions = priceAlertSuggestions(product);
  // STEP69: closest-priced rivals in the same category (other makers
  // first) - each links to its "A vs B" comparison page.
  const rivals = nearestRivals(product, categoryProducts, 3);
  const compareProducts = [
    product,
    ...categoryProducts
      .filter((p) => p.id !== product.id && p.buy_signal_score !== null)
      .sort((a, b) => (b.buy_signal_score ?? 0) - (a.buy_signal_score ?? 0))
      .slice(0, 2),
  ];

  const siteUrl = SITE_URL;
  // Same normalized URL the photo itself loads from (https, or null when
  // unusable) - never an http:// or malformed value in the JSON-LD.
  const imageUrl = normalizeImageUrl(product.image_url);

  // Product markup (product-snippet shape - see lib/productJsonLd.ts for
  // why this is an AggregateOffer and carries no shipping/return policy).
  const jsonLd = buildProductJsonLd({ product, siteUrl, description: productSeoDescription(product) });

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
        <div className="mx-auto max-w-7xl px-6 py-4 sm:py-8">
          <Link href={`/category/${product.category}`} className="text-xs font-medium uppercase tracking-widest text-foreground/40 hover:text-brand">
            ← {CATEGORY_LABELS[product.category] ?? product.category}
          </Link>
        </div>
      </div>

      <div className="mx-auto max-w-7xl px-6 py-6 sm:py-16">
        <div className="grid grid-cols-1 gap-6 sm:gap-12 lg:grid-cols-2 lg:gap-16">
          <FadeIn className="flex flex-col gap-2">
            {/* STEP65: shorter on a phone so the price and shop button reach
                the first screen. */}
            <div className="relative aspect-[4/3] max-h-[240px] w-full overflow-hidden rounded-2xl border border-border bg-card sm:aspect-square sm:max-h-none">
              <SafeProductImage
                src={product.image_url}
                alt={product.name}
                category={product.category}
                className="object-contain p-5 sm:p-10"
              />
            </div>
            {imageUrl && new URL(imageUrl, SITE_URL).hostname.endsWith("rakuten.co.jp") && (
              <p className="text-right text-[11px] text-foreground/35">画像提供: 楽天市場</p>
            )}
            {/* STEP61: fills the space under the photo on desktop; on a phone
                it comes after the buy block instead (below), so the price
                and shop buttons stay near the top. */}
            <ProductOverview product={product} className="mt-4 hidden lg:block" />
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
                    <span className="rounded-full bg-brand px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-widest text-on-brand">
                      {popularityBadge.label}
                    </span>
                  )}
                  {badge && (
                    <span
                      className={`rounded-full px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-widest ${
                        badge.tone === "strong"
                  ? `bg-brand text-on-brand ${badge.label === "過去最安値圏" ? "glow-emerald" : ""}`
                  : "border border-border-strong bg-white text-foreground/75"
                      }`}
                    >
                      {badge.label === "過去最安値圏" && <span className="live-dot mr-1.5 align-middle" aria-hidden="true" />}
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
                  <span className="text-[10px] font-bold uppercase tracking-widest text-emerald-700 dark:text-emerald-500">
                    実績
                  </span>
                  <span className="text-xs text-foreground/40">
                    {comparedOffers ? `現在の最安値（${shopOffers.length}店舗を比較）` : "現在価格"}
                  </span>
                </div>
                <span className="font-num text-4xl font-semibold text-foreground">
                  {yen(displayPrice)}
                </span>
                {product.category === "iron" && (
                  <span className="text-xs text-foreground/55">5〜6本セット価格（単品の価格ではありません）</span>
                )}
                {comparedOffers && lowestOffer && (
                  <span className="text-xs text-foreground/55">
                    <span className="font-semibold text-brand dark:text-brand-light">{lowestOffer.label}</span>が最安
                    {otherOffers.map((offer) => (
                      <span key={offer.shop} className="ml-2 text-foreground/40">
                        {offer.label} <span className="font-num">{yen(offer.price)}</span>
                      </span>
                    ))}
                  </span>
                )}
                {msrpPct !== null && (
                  <span className={`text-sm font-semibold ${msrpPct < 0 ? "text-brand dark:text-brand-light" : "text-foreground/50"}`}>
                    {msrpPct > 0 ? "+" : ""}
                    {msrpPct}% 定価より
                  </span>
                )}
                {hasReliableTrend && product.price_change_percent !== null ? (
                  <span className={msrpPct !== null ? "text-xs text-foreground/40" : "text-sm font-semibold " + (product.price_change_percent < 0 ? "text-brand dark:text-brand-light" : "text-foreground/50")}>
                    {product.price_change_percent > 0 ? "+" : ""}
                    {lowestOffer?.shop === "yahoo" ? "楽天価格 " : ""}
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

            {/* STEP65 (CRO): moved right under the price card - it used to sit
                after four explanation cards, ~2.4 phone screens down.
                STEP57: every shop, one tap from the top of the page. The
                cheapest fetched price (or Rakuten when there's nothing to
                compare) is the main button; the other shops - Amazon
                included - sit right under it. Same rows as the board below
                (lib/shopRows.ts). */}
            <div id="buy-box" className="card-lux flex scroll-mt-24 flex-col gap-3 rounded-2xl p-5">
              <div className="flex items-baseline justify-between gap-3">
                <span className="text-xs text-foreground/45">
                  {comparedOffers && lowestOffer
                    ? `現在の最安値（${lowestOffer.label}）`
                    : !lowestOffer && primaryShop?.stale
                      ? `最後に取得した価格（${primaryShop.ageDays ?? "?"}日前）`
                      : "現在価格"}
                  {product.category === "iron" && "・5〜6本セット"}
                </span>
                <span className="font-num text-2xl font-semibold text-foreground">{yen(displayPrice)}</span>
              </div>
              {primaryShop && (
                <TrackedCta
                  href={primaryShop.url}
                  target="_blank"
                  rel={primaryShop.sponsored ? "noopener noreferrer sponsored" : "noopener noreferrer"}
                  className="btn-shop tap whitespace-nowrap rounded-full px-5 py-4 text-center text-sm font-semibold sm:px-6 sm:text-base"
                  event="cta_click"
                  params={{
                    product_id: product.id,
                    product_slug: product.slug,
                    product_name: product.name,
                    cta_type: primaryShop.ctaType,
                    shop: primaryShop.key,
                    buy_score: product.buy_score,
                  }}
                  productId={product.id}
                  category={product.category}
                  placement="product_detail_cta"
                >
                  {primaryShop.isLowest ? `${primaryShop.label}で見る（最安）` : `${primaryShop.label}で価格を見る`}
                  <CtaArrow />
                </TrackedCta>
              )}
              {primaryShop && (
                <p className="-mt-1 text-center text-[11px] text-foreground/45">
                  {primaryShop.stale
                    ? `${staleLabel(primaryShop)}です。最新の価格・在庫・送料は${primaryShop.label}のページで確認できます`
                    : `在庫・送料・ポイントは${primaryShop.label}のページで確認できます`}
                </p>
              )}
              {secondaryShops.length > 0 && (
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                  {secondaryShops.map((row) => (
                    <TrackedCta
                      key={`${row.key}-${row.url}`}
                      href={row.url}
                      target="_blank"
                      rel={row.sponsored ? "noopener noreferrer sponsored" : "noopener noreferrer"}
                      className="btn-ghost tap flex items-center gap-2.5 rounded-full py-2.5 pl-2.5 pr-4 text-sm font-semibold text-foreground/80 hover:text-foreground"
                      event="cta_click"
                      params={{
                        product_id: product.id,
                        product_slug: product.slug,
                        product_name: product.name,
                        cta_type: row.ctaType,
                        shop: row.key,
                        buy_score: product.buy_score,
                      }}
                      productId={product.id}
                      category={product.category}
                      placement="product_detail_cta_alt"
                    >
                      <span
                        aria-hidden="true"
                        className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-[11px] font-bold ${SHOP_MARKS[row.key].className}`}
                      >
                        {SHOP_MARKS[row.key].glyph}
                      </span>
                      <span className="flex-1 truncate text-left">{row.label}</span>
                      <span className="font-num text-xs text-foreground/55">
                        {row.kind === "price" && row.price !== null
                          ? row.stale
                            ? `${yen(row.price)}（${row.ageDays ?? "?"}日前）`
                            : yen(row.price)
                          : "価格を見る"}
                      </span>
                    </TrackedCta>
                  ))}
                </div>
              )}
              <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
                <a href="#store-comparison" className="text-xs font-semibold text-brand hover:underline dark:text-brand-light">
                  全ショップの価格を比較する ↓
                </a>
                {officialShop && (
                  <TrackedCta
                    href={officialShop.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs font-semibold text-foreground/50 hover:text-foreground"
                    event="cta_click"
                    params={{
                      product_id: product.id,
                      product_slug: product.slug,
                      product_name: product.name,
                      cta_type: "official",
                      buy_score: product.buy_score,
                    }}
                  >
                    メーカー商品ページ →
                  </TrackedCta>
                )}
              </div>
              <p className="text-xs leading-relaxed text-foreground/65">
                ※広告・PRを含みます。リンクにはアフィリエイトリンクが含まれ、リンク経由の購入により当サイトが紹介料を受け取ることがあります。価格・在庫は変動するため、購入前に販売元サイトでご確認ください。
              </p>
            </div>

            {hasReliableTrend && product.buy_signal_score !== null && (
              <ScoreExplanation product={product} />
            )}

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
                  <span className="font-semibold text-foreground/70">要確認：</span>
                  通常価格帯から大きく外れた値下がりです。掲載元での価格反映のタイムラグや、
                  商品の取り違えなどの可能性もゼロではありません。購入前に実際の販売ページで価格をご確認ください。
                </p>
              )}
            </div>

            {showInlineAlert && (
              <PriceAlertForm
                slug={product.slug}
                currentPrice={product.current_price}
                variant="inline"
                suggestions={alertSuggestions}
              />
            )}

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
                  <dd className="mt-1 font-num text-base font-medium text-foreground">{yen(product.msrp)}</dd>
                </div>
              )}
              <div>
                <dt>
                  過去30日平均
                  {rakutenSeriesSuffix}
                </dt>
                {hasReliableTrend ? (
                  <dd className="mt-1 font-num text-base font-medium text-foreground">
                    {yen(product.average_price)}
                  </dd>
                ) : (
                  <dd className="mt-1 text-[11px] font-medium leading-snug text-foreground/40">分析準備中</dd>
                )}
              </div>
              <div>
                <dt>
                  過去最安値
                  {rakutenSeriesSuffix}
                </dt>
                <dd className="mt-1 font-num text-base font-medium text-foreground">{yen(product.lowest_price)}</dd>
              </div>
              <div>
                <dt>
                  前回価格
                  {rakutenSeriesSuffix}
                </dt>
                <dd className="mt-1 font-num text-base font-medium text-foreground">{yen(product.previous_price)}</dd>
              </div>
            </dl>

          </FadeIn>
        </div>


        {/* STEP57 order: shops first (where to buy, cheapest highlighted),
            then the price history, then related products. */}
        <ProductOverview product={product} className="mt-10 lg:hidden" />

        <FadeIn id="store-comparison" className="mt-12 scroll-mt-20">
          <StoreComparisonTable product={product} lastUpdatedAt={lastPriceUpdatedAt} />
        </FadeIn>

        <FadeIn className="mt-10 rounded-2xl border border-border bg-card p-6 sm:p-10">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium uppercase tracking-[0.3em] text-accent">Price History</span>
            <span className="text-[10px] font-bold uppercase tracking-widest text-emerald-700 dark:text-emerald-500">
              実績
            </span>
          </div>
          <h2 className="mt-2 font-display text-2xl font-semibold text-foreground">価格推移</h2>
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

          <div className="mt-10 border-t border-border pt-10">
            <h3 className="font-display text-lg font-semibold text-foreground">長期価格推移（月次・最大3年）</h3>
            <div className="mt-6">
              <MonthlyTrendChart history={product.price_history} />
            </div>
          </div>

          <div className="mt-10 border-t border-border pt-10">
            <PriceTimeline product={product} />
          </div>
        </FadeIn>

        <FadeIn className="mt-10 border-t border-border pt-10">
          <PriceForecast product={product} />
        </FadeIn>

        {compareProducts.length >= 2 && (
          <FadeIn className="mt-10">
            <span className="text-xs font-medium uppercase tracking-[0.3em] text-accent">Related</span>
            <h2 className="mt-2 font-display text-2xl font-semibold text-foreground">関連商品・同じカテゴリの候補と比較</h2>
            {rivals.length > 0 && (
              <div className="mt-4 flex flex-wrap gap-2">
                <span className="self-center text-xs text-foreground/45">価格帯の近いモデルと比較:</span>
                {rivals.map((r) => (
                  <Link
                    key={r.slug}
                    href={pairHref(product.slug, r.slug)}
                    className="rounded-full border border-border bg-background px-3.5 py-1.5 text-xs font-semibold text-foreground/70 hover:border-brand/40 hover:text-brand"
                  >
                    vs {r.brand} {r.name}
                  </Link>
                ))}
              </div>
            )}
            <div className="mt-6">
              <CompareStrip products={compareProducts} currentId={product.id} />
            </div>
          </FadeIn>
        )}


        {/* STEP52: AI-picked consumables, directly under the price
            comparison table (this product itself is left out). */}
        <ConsumablesCorner variant="product" excludeProductId={product.id} />

        {alertsEnabled && !showInlineAlert && (
          <FadeIn className="mt-10">
            <PriceAlertForm slug={product.slug} currentPrice={product.current_price} suggestions={alertSuggestions} />
          </FadeIn>
        )}

        {product.ai_summary && product.ai_summary !== product.buy_reason && (
          <FadeIn className="mt-10 border-t border-border pt-10">
            <span className="text-xs font-medium uppercase tracking-[0.3em] text-accent">More Detail</span>
            <h2 className="mt-2 font-display text-2xl font-semibold text-foreground">価格データからわかること</h2>
            <div className="mt-5 flex flex-col gap-4 text-sm leading-relaxed text-foreground/70">
              <p>{product.ai_summary}</p>
            </div>
          </FadeIn>
        )}

        {product.ai_caution && (
          <p className="mt-8 rounded-xl border border-border bg-card px-4 py-3 text-xs text-foreground/45">
            <span className="font-semibold text-foreground/70">補足：</span> {product.ai_caution}
          </p>
        )}

        <FadeIn className="mt-10 border-t border-border pt-10">
          <ProductFAQ product={product} />
        </FadeIn>

        <FadeIn className="mt-10 border-t border-border pt-10">
          <DataSourceNote />
        </FadeIn>
      </div>
      {/* room for the pinned buy bar, so it never covers the page's last lines */}
      {stickyShop && <div aria-hidden="true" className="h-20" />}
      {stickyShop && (
        <StickyBuyBar
          href={stickyShop.url}
          shopLabel={stickyShop.label}
          price={stickyPrice !== null ? yen(stickyPrice) : null}
          isLowest={stickyShop.isLowest}
          sponsored={stickyShop.sponsored}
          productName={product.name}
          trackParams={{
            product_id: product.id,
            product_slug: product.slug,
            product_name: product.name,
            cta_type: stickyShop.ctaType,
            shop: stickyShop.key,
            buy_score: product.buy_score,
          }}
          productId={product.id}
          category={product.category}
        />
      )}
    </article>
  );
}
