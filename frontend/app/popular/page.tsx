import type { Metadata } from "next";
import Link from "next/link";

import FadeIn from "@/components/FadeIn";
import PageHeader from "@/components/PageHeader";
import ProductCard from "@/components/ProductCard";
import { CATEGORIES, CATEGORY_LABELS, Product, getProducts } from "@/lib/api";
import { POPULARITY_MAX_AGE_DAYS, freshPopularityRank, latestPopularityUpdate } from "@/lib/popularity";

export const revalidate = 0;

// Same threshold ProductCard/product page use for "enough data to claim a
// trend" - kept local rather than shared since each of these files already
// defines its own copy of this constant (see ProductCard.tsx).
const THIN_DATA_DAYS = 7;

export const metadata: Metadata = {
  title: "人気ランキング",
  description: "楽天市場の実際の売れ筋ランキングをもとに、人気のゴルフ用品と価格の動きを確認できます。",
};

function isPriceDropping(p: Product): boolean {
  if (p.msrp !== null && p.current_price !== null && p.current_price < p.msrp) return true;
  const reliable = p.buy_score !== "insufficient_data" && p.history_span_days >= THIN_DATA_DAYS;
  return reliable && p.price_change_percent !== null && p.price_change_percent < 0;
}

// Only ranks re-confirmed within the last few days (lib/popularity.ts) - a
// rank left over from a sync that has since stopped succeeding isn't
// "popular now". A plain helper (not inline in the component) so the
// clock read inside freshPopularityRank doesn't trip the purity lint rule;
// the page re-renders per request anyway (revalidate = 0).
function freshlyRanked(products: Product[]) {
  const ranks = new Map(products.map((p) => [p.id, freshPopularityRank(p)]));
  const rankOf = (p: Product) => ranks.get(p.id) ?? 999;
  return { ranked: products.filter((p) => ranks.get(p.id) != null), rankOf };
}

export default async function PopularPage() {
  let products: Product[] = [];
  let error: string | null = null;
  try {
    products = await getProducts({ limit: 200 });
  } catch {
    error = "商品情報の取得に失敗しました。しばらくしてから再度お試しください。";
  }

  const { ranked, rankOf } = freshlyRanked(products);
  const lastUpdated = latestPopularityUpdate(ranked);
  const popularAndDropping = ranked.filter(isPriceDropping).sort((a, b) => rankOf(a) - rankOf(b));

  const byCategory = CATEGORIES.map((c) => ({
    category: c,
    products: ranked.filter((p) => p.category === c).sort((a, b) => rankOf(a) - rankOf(b)),
  })).filter((g) => g.products.length > 0);

  return (
    <div>
      <PageHeader
        eyebrow="Popular"
        title="人気ランキング"
        description={`楽天市場の実際のカテゴリ別売れ筋ランキングをもとにしています。当サイト独自の推測ではありません。${
          lastUpdated
            ? `（ランキング最終取得：${lastUpdated.toLocaleString("ja-JP", { timeZone: "Asia/Tokyo", month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" })}）`
            : ""
        }`}
        collageImages={ranked.map((p) => p.image_url)}
      />

      {error && (
        <div className="mx-auto max-w-7xl px-6 py-16">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}

      {!error && popularAndDropping.length > 0 && (
        <section className="border-b border-border px-6 py-16 sm:py-20">
          <div className="mx-auto max-w-7xl">
            <FadeIn className="flex flex-col gap-3">
              <span className="text-xs font-medium uppercase tracking-[0.3em] text-sale">Popular &amp; Dropping</span>
              <h2 className="max-w-lg font-display text-3xl font-semibold leading-tight text-foreground sm:text-4xl">
                人気なのに値下がり中
              </h2>
              <p className="max-w-lg text-sm text-foreground/55">
                楽天市場で実際に売れているのに、価格が下がっている商品です。
              </p>
            </FadeIn>
            <div className="mt-10 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {popularAndDropping.map((product, i) => (
                <FadeIn key={product.id} delay={i * 90}>
                  <ProductCard product={product} listSource="popular_dropping" />
                </FadeIn>
              ))}
            </div>
          </div>
        </section>
      )}

      {!error && ranked.length === 0 && (
        <div className="mx-auto max-w-7xl px-6 py-16">
          <p className="rounded-2xl border border-dashed border-border bg-card px-4 py-16 text-center text-sm text-foreground/50">
            現在、直近{POPULARITY_MAX_AGE_DAYS}日以内に確認できた楽天市場の売れ筋ランキングに、当サイトの掲載商品は入っていません。ランキングは毎朝更新されます。
          </p>
        </div>
      )}

      {!error &&
        byCategory.map(({ category, products: categoryProducts }) => (
          <section key={category} className="border-t border-border px-6 py-16 sm:py-20">
            <div className="mx-auto max-w-7xl">
              <div className="flex items-center justify-between">
                <h2 className="font-display text-2xl font-semibold text-foreground">
                  {CATEGORY_LABELS[category]}の人気ランキング
                </h2>
                <Link href={`/category/${category}`} className="text-xs font-semibold text-brand hover:underline">
                  カテゴリ全体を見る →
                </Link>
              </div>
              <div className="mt-8 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
                {categoryProducts.map((product, i) => (
                  <FadeIn key={product.id} delay={(i % 6) * 60}>
                    <ProductCard product={product} listSource="popular_category" />
                  </FadeIn>
                ))}
              </div>
            </div>
          </section>
        ))}
    </div>
  );
}
