import Link from "next/link";

import AiBuySignal from "@/components/AiBuySignal";
import FadeIn from "@/components/FadeIn";
import ForecastPreviewCard from "@/components/ForecastPreviewCard";
import Hero from "@/components/Hero";
import HowItWorks from "@/components/HowItWorks";
import Newsletter from "@/components/Newsletter";
import ProductCard from "@/components/ProductCard";
import { BUY_SCORE_LABELS, getProducts } from "@/lib/api";
import { computeDeals } from "@/lib/deals";

function yen(value: number | null): string {
  if (value === null) return "-";
  return `¥${value.toLocaleString("ja-JP")}`;
}

export const revalidate = 0;

const FILTER_TABS = ["all", "strong_buy", "buy", "neutral", "not_buy"] as const;
type FilterTab = (typeof FILTER_TABS)[number];

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

  const withPct = allProducts.filter((p) => p.price_change_percent !== null);
  const avgDiscount = withPct.length
    ? Math.round((withPct.reduce((sum, p) => sum + (p.price_change_percent ?? 0), 0) / withPct.length) * 10) / 10
    : null;

  const bestBuy = allProducts.slice(0, 5);
  const topDeals = computeDeals(allProducts).slice(0, 3);
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

  return (
    <div className="flex flex-col">
      <Hero productCount={allProducts.length} avgDiscount={avgDiscount} />

      {error && (
        <div className="mx-auto max-w-7xl px-6 py-16">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}

      {!error && bestBuy.length > 0 && (
        <section id="best-buy" className="scroll-mt-20 bg-background px-6 py-24 sm:py-32">
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
                🔮 Price Forecast
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

      {!error && (
        <section className="border-t border-border bg-background px-6 py-24 sm:py-32">
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
