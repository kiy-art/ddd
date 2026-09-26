import Link from "next/link";

import AiBuySignal from "@/components/AiBuySignal";
import FadeIn from "@/components/FadeIn";
import ForecastPreviewCard from "@/components/ForecastPreviewCard";
import Hero from "@/components/Hero";
import HowItWorks from "@/components/HowItWorks";
import Newsletter from "@/components/Newsletter";
import ProductCard from "@/components/ProductCard";
import { BUY_SCORE_LABELS, Product, TrendingProducts, getProducts, getTrendingProducts } from "@/lib/api";
import { computeDeals } from "@/lib/deals";
import { getFallbackValueScore } from "@/lib/fallbackScore";
import { GUIDES } from "@/lib/guides";

function yen(value: number | null): string {
  if (value === null) return "-";
  return `¥${value.toLocaleString("ja-JP")}`;
}

export const revalidate = 0;

const FILTER_TABS = ["all", "strong_buy", "buy", "neutral", "not_buy"] as const;
type FilterTab = (typeof FILTER_TABS)[number];

// Same threshold used elsewhere (ProductCard, product detail page) for
// "enough price history to claim a trend" - each file keeps its own copy.
const THIN_DATA_DAYS = 7;

function isFilterTab(value: string | undefined): value is FilterTab {
  return !!value && (FILTER_TABS as readonly string[]).includes(value);
}

export default async function Home({
  searchParams,
}: {
  searchParams: Promise<{ buy_score?: string }>;
}) {
  const params = await searchParams;
  const activeTab: FilterTab = isFilterTab(params.buy_score) ? params.buy_score : "all";

  let allProducts: Awaited<ReturnType<typeof getProducts>> = [];
  let listProducts: Awaited<ReturnType<typeof getProducts>> = [];
  let error: string | null = null;

  try {
    allProducts = await getProducts();
    listProducts = activeTab === "all" ? allProducts : await getProducts({ buy_score: activeTab });
  } catch {
    error = "商品情報の取得に失敗しました。しばらくしてから再度お試しください。";
  }

  // STEP42: real, dated AI decision (see app/content_optimizer.py's
  // reorder_homepage action) - not a live re-ranking, so it stays stable
  // for the day. Empty (never padded) until the daily optimization run has
  // produced a decision with real click data behind it.
  let trending: TrendingProducts = { decision_basis: null, products: [] };
  try {
    trending = await getTrendingProducts();
  } catch {
    // best-effort - a failed fetch just means the section doesn't render
  }

  const withPct = allProducts.filter((p) => p.price_change_percent !== null);
  const avgDiscount = withPct.length
    ? Math.round((withPct.reduce((sum, p) => sum + (p.price_change_percent ?? 0), 0) / withPct.length) * 10) / 10
    : null;

  // "AIが選んだ、今日の買い時" needs to actually be ranked, not an arbitrary
  // slice of whatever order the API returned. Real price-history-backed
  // picks (strong_buy/buy with enough history) come first; when the
  // catalog doesn't yet have 5 of those (still common while price history
  // is thin - see lib/fallbackScore.ts), the remaining slots are filled by
  // the same real MSRP-based fallback score the product page itself falls
  // back to, ranked the same way - never an arbitrary pad.
  const BEST_BUY_COUNT = 5;
  const reliableBestBuy = allProducts
    .filter((p) => (p.buy_score === "strong_buy" || p.buy_score === "buy") && p.history_span_days >= THIN_DATA_DAYS)
    .sort((a, b) => (b.buy_signal_score ?? 0) - (a.buy_signal_score ?? 0));

  let bestBuy: Product[] = reliableBestBuy.slice(0, BEST_BUY_COUNT);
  if (bestBuy.length < BEST_BUY_COUNT) {
    const usedIds = new Set(bestBuy.map((p) => p.id));
    const fallbackRanked = allProducts
      .filter((p) => !usedIds.has(p.id))
      .map((p) => ({
        product: p,
        fallback: getFallbackValueScore({ msrp: p.msrp, current_price: p.current_price, release_date: p.release_date }),
      }))
      .filter(
        (entry): entry is { product: Product; fallback: NonNullable<ReturnType<typeof getFallbackValueScore>> } =>
          entry.fallback !== null
      )
      .sort((a, b) => b.fallback.score - a.fallback.score)
      .map((entry) => entry.product);
    bestBuy = [...bestBuy, ...fallbackRanked].slice(0, BEST_BUY_COUNT);
  }

  const topDeals = computeDeals(allProducts).slice(0, 3);
  const popularAndDropping = allProducts
    .filter((p) => {
      if (p.popularity_rank === null) return false;
      if (p.msrp !== null && p.current_price !== null && p.current_price < p.msrp) return true;
      const reliable = p.buy_score !== "insufficient_data" && p.history_span_days >= THIN_DATA_DAYS;
      return reliable && p.price_change_percent !== null && p.price_change_percent < 0;
    })
    .sort((a, b) => (a.popularity_rank ?? 999) - (b.popularity_rank ?? 999))
    .slice(0, 3);
  const forecastPicks = allProducts
    .filter(
      (p) =>
        p.forecast_trend === "down" &&
        p.current_price !== null &&
        p.forecast_center_price !== null &&
        p.forecast_low_price !== null &&
        p.forecast_high_price !== null &&
        p.forecast_target_date !== null
    )
    .sort((a, b) => (b.current_price! - b.forecast_center_price!) - (a.current_price! - a.forecast_center_price!))
    .slice(0, 3);
  const topRanked = [...allProducts]
    .sort((a, b) => (b.buy_signal_score ?? -1) - (a.buy_signal_score ?? -1))
    .slice(0, 5);

  const heroImages = [...bestBuy, ...allProducts].map((p) => p.image_url).filter(Boolean).slice(0, 6);
  const featuredGuides = GUIDES.filter((g) => g.featured);

  return (
    <div className="flex flex-col">
      <Hero productCount={allProducts.length} avgDiscount={avgDiscount} collageImages={heroImages} />

      {featuredGuides.length > 0 && (
        <section className="border-t border-border bg-background px-6 py-12 sm:py-16">
          <div className="mx-auto max-w-7xl">
            <FadeIn className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <span className="text-xs font-medium uppercase tracking-[0.3em] text-accent">Featured Guides</span>
                <h2 className="mt-2 font-display text-xl font-semibold text-foreground sm:text-2xl">
                  注目の特集ガイド
                </h2>
                <p className="mt-1 text-sm text-foreground/55">実際の価格データに基づいた、今チェックしたい商品の特集です。</p>
              </div>
              <Link
                href="/guides"
                className="shrink-0 rounded-full border border-border px-4 py-2 text-xs font-semibold text-foreground/70 transition-colors hover:border-brand/40 hover:text-brand dark:hover:text-brand-light"
              >
                購入ガイド一覧を見る →
              </Link>
            </FadeIn>

            <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {featuredGuides.map((guide, i) => (
                <FadeIn key={guide.slug} delay={i * 80}>
                  <Link
                    href={`/guides/${guide.slug}`}
                    className="block h-full rounded-2xl border border-brand/30 bg-card p-5 transition-colors hover:border-brand/60 sm:p-6"
                  >
                    <h3 className="font-display text-base font-semibold leading-snug text-foreground">
                      {guide.title}
                    </h3>
                    <p className="mt-2 line-clamp-2 text-xs leading-relaxed text-foreground/55">
                      {guide.description}
                    </p>
                  </Link>
                </FadeIn>
              ))}
            </div>
          </div>
        </section>
      )}

      {error && (
        <div className="mx-auto max-w-7xl px-6 py-16">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}

      {!error && bestBuy.length > 0 && (
        <section id="best-buy" className="scroll-mt-20 bg-card px-6 py-24 sm:py-32">
          <div className="mx-auto max-w-7xl">
            <FadeIn className="flex flex-col gap-3">
              <span className="text-xs font-medium uppercase tracking-[0.3em] text-accent">
                Today&apos;s Best Buy
              </span>
              <h2 className="max-w-lg font-display text-3xl font-semibold leading-tight text-foreground sm:text-4xl">
                AIが選んだ、今日の買い時。
              </h2>
              <p className="max-w-lg text-sm text-foreground/55">
                厳選した{bestBuy.length}商品だけを表示しています。
              </p>
            </FadeIn>

            <div className="mt-12 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {bestBuy.map((product, i) => (
                <FadeIn key={product.id} delay={i * 90}>
                  <ProductCard product={product} listSource="homepage_best_buy" />
                </FadeIn>
              ))}
            </div>
          </div>
        </section>
      )}

      {!error && popularAndDropping.length > 0 && (
        <section className="border-t border-border bg-background px-6 py-24 sm:py-32">
          <div className="mx-auto max-w-7xl">
            <FadeIn className="flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <span className="text-xs font-medium uppercase tracking-[0.3em] text-sale">
                  Popular &amp; Dropping
                </span>
                <h2 className="mt-3 font-display text-3xl font-semibold leading-tight text-foreground sm:text-4xl">
                  人気なのに値下がり中
                </h2>
                <p className="mt-3 max-w-lg text-sm text-foreground/55">
                  楽天市場の実際の売れ筋ランキングに入っているのに、価格が下がっている商品です。
                </p>
              </div>
              <Link
                href="/popular"
                className="rounded-full border border-border px-4 py-2 text-xs font-semibold text-foreground/70 transition-colors hover:border-brand/40 hover:text-brand dark:hover:text-brand-light"
              >
                すべて見る →
              </Link>
            </FadeIn>

            <div className="mt-12 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {popularAndDropping.map((product, i) => (
                <FadeIn key={product.id} delay={i * 90}>
                  <ProductCard product={product} listSource="homepage_popular_dropping" />
                </FadeIn>
              ))}
            </div>
          </div>
        </section>
      )}

      {!error && trending.products.length > 0 && (
        <section className="border-t border-border bg-card px-6 py-24 sm:py-32">
          <div className="mx-auto max-w-7xl">
            <FadeIn className="flex flex-col gap-3">
              <span className="text-xs font-medium uppercase tracking-[0.3em] text-accent">Trending Now</span>
              <h2 className="max-w-lg font-display text-3xl font-semibold leading-tight text-foreground sm:text-4xl">
                今、注目されているギア
              </h2>
              <p className="max-w-lg text-sm text-foreground/55">
                実際のクリック数をもとに、直近よく見られている商品をまとめました。
              </p>
            </FadeIn>

            <div className="mt-12 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {trending.products.map((product, i) => (
                <FadeIn key={product.id} delay={i * 90}>
                  <ProductCard product={product} listSource="homepage_trending" />
                </FadeIn>
              ))}
            </div>
          </div>
        </section>
      )}

      {!error && topDeals.length > 0 && (
        <section className="border-t border-border bg-card px-6 py-24 sm:py-32">
          <div className="mx-auto max-w-7xl">
            <FadeIn className="flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <span className="text-xs font-medium uppercase tracking-[0.3em] text-accent">
                  Today&apos;s Price Drops
                </span>
                <h2 className="mt-3 font-display text-3xl font-semibold leading-tight text-foreground sm:text-4xl">
                  価格が下がった商品
                </h2>
              </div>
              <Link
                href="/deals"
                className="rounded-full border border-border px-4 py-2 text-xs font-semibold text-foreground/70 transition-colors hover:border-brand/40 hover:text-brand dark:hover:text-brand-light"
              >
                すべて見る →
              </Link>
            </FadeIn>

            <div className="mt-12 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {topDeals.map(({ product, dropPercent }, i) => (
                <FadeIn key={product.id} delay={i * 90} className="flex flex-col gap-2">
                  <span className="px-1 text-xs font-semibold text-brand dark:text-brand-light">
                    前回価格より {dropPercent}% 値下がり
                  </span>
                  <ProductCard product={product} listSource="homepage_price_drops" />
                </FadeIn>
              ))}
            </div>
          </div>
        </section>
      )}

      {!error && forecastPicks.length > 0 && (
        <section className="border-t border-border bg-background px-6 py-24 sm:py-32">
          <div className="mx-auto max-w-7xl">
            <FadeIn className="flex flex-col gap-3">
              <span className="text-xs font-medium uppercase tracking-[0.3em] text-accent">
                Price Forecast
              </span>
              <h2 className="max-w-lg font-display text-3xl font-semibold leading-tight text-foreground sm:text-4xl">
                今後、値下がりが期待される商品
              </h2>
              <p className="max-w-lg text-sm text-foreground/55">
                過去の価格データをもとにした予測情報です。将来価格を保証するものではありません。
              </p>
            </FadeIn>

            <div className="mt-12 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {forecastPicks.map((product, i) => (
                <FadeIn key={product.id} delay={i * 90}>
                  <ForecastPreviewCard product={product} />
                </FadeIn>
              ))}
            </div>
          </div>
        </section>
      )}

      {!error && topRanked.length > 0 && (
        <section className="border-t border-border bg-card px-6 py-24 sm:py-32">
          <div className="mx-auto max-w-7xl">
            <FadeIn className="flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <span className="text-xs font-medium uppercase tracking-[0.3em] text-accent">
                  Ranking
                </span>
                <h2 className="mt-3 font-display text-3xl font-semibold leading-tight text-foreground sm:text-4xl">
                  買い時ランキング
                </h2>
              </div>
              <Link
                href="/ranking"
                className="rounded-full border border-border px-4 py-2 text-xs font-semibold text-foreground/70 transition-colors hover:border-brand/40 hover:text-brand dark:hover:text-brand-light"
              >
                すべて見る →
              </Link>
            </FadeIn>

            <ol className="mt-12 flex flex-col gap-3">
              {topRanked.map((product, i) => (
                <FadeIn key={product.id} delay={i * 60}>
                  <Link
                    href={`/products/${product.slug}`}
                    className="flex items-center gap-4 rounded-2xl border border-border bg-card p-4 transition-colors hover:border-brand/40 sm:p-5"
                  >
                    <span className="w-10 shrink-0 text-center font-display text-2xl font-semibold text-foreground/25">
                      {i + 1}
                    </span>
                    <div className="min-w-0 flex-1">
                      <span className="text-[11px] font-medium uppercase tracking-widest text-foreground/40">
                        {product.brand}
                      </span>
                      <div className="truncate font-display text-base font-medium text-foreground">
                        {product.name}
                      </div>
                      <div className="mt-1 text-sm text-foreground/50">{yen(product.current_price)}</div>
                    </div>
                    <AiBuySignal
                      buyScore={product.buy_score}
                      buySignalScore={product.buy_signal_score}
                      historySpanDays={product.history_span_days}
                      size="sm"
                    />
                  </Link>
                </FadeIn>
              ))}
            </ol>
          </div>
        </section>
      )}

      <section className="border-t border-border bg-background px-6 py-24 sm:py-32">
        <div className="mx-auto flex max-w-7xl flex-col items-start gap-6 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <span className="text-xs font-medium uppercase tracking-[0.3em] text-accent">Golf Club Finder</span>
            <h2 className="mt-3 font-display text-3xl font-semibold leading-tight text-foreground sm:text-4xl">
              あなたに合うクラブを診断
            </h2>
            <p className="mt-3 max-w-md text-sm text-foreground/55">
              カテゴリと予算を選ぶだけで、今チェックすべき商品を価格データから絞り込みます。
            </p>
          </div>
          <Link
            href="/finder"
            className="shrink-0 rounded-full bg-brand px-8 py-3.5 text-sm font-semibold text-white transition-transform hover:scale-[1.02]"
          >
            診断してみる →
          </Link>
        </div>
      </section>

      {!error && (
        <section className="border-t border-border bg-card px-6 py-24 sm:py-32">
          <div className="mx-auto max-w-7xl">
            <FadeIn className="flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <span className="text-xs font-medium uppercase tracking-[0.3em] text-accent">
                  Browse All
                </span>
                <h2 className="mt-3 font-display text-3xl font-semibold leading-tight text-foreground sm:text-4xl">
                  すべてのゴルフ用品
                </h2>
              </div>
              <div className="flex flex-wrap gap-2">
                {FILTER_TABS.map((tab) => (
                  <Link
                    key={tab}
                    href={tab === "all" ? "/" : `/?buy_score=${tab}`}
                    className={`rounded-full border px-3.5 py-1.5 text-xs font-semibold transition-colors ${
                      activeTab === tab
                        ? "border-brand bg-brand text-white"
                        : "border-border bg-background text-foreground/60 hover:border-brand/40 hover:text-brand dark:hover:text-brand-light"
                    }`}
                  >
                    {tab === "all" ? "すべて" : BUY_SCORE_LABELS[tab]}
                  </Link>
                ))}
              </div>
            </FadeIn>

            {listProducts.length === 0 ? (
              <p className="mt-12 rounded-2xl border border-dashed border-border bg-background px-4 py-12 text-center text-sm text-foreground/50">
                現在表示できる商品がありません。価格データが蓄積され次第表示されます。
              </p>
            ) : (
              <div className="mt-12 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
                {listProducts.map((product, i) => (
                  <FadeIn key={product.id} delay={(i % 6) * 60}>
                    <ProductCard product={product} listSource="homepage_browse_all" />
                  </FadeIn>
                ))}
              </div>
            )}
          </div>
        </section>
      )}

      <HowItWorks />
      <Newsletter />
    </div>
  );
}
