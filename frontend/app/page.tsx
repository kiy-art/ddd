import Link from "next/link";

import FadeIn from "@/components/FadeIn";
import Hero from "@/components/Hero";
import HowItWorks from "@/components/HowItWorks";
import Newsletter from "@/components/Newsletter";
import ProductCard from "@/components/ProductCard";
import { BUY_SCORE_LABELS, getProducts } from "@/lib/api";

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
                  <ProductCard product={product} />
                </FadeIn>
              ))}
            </div>
          </div>
        </section>
      )}

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
                    <ProductCard product={product} />
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
