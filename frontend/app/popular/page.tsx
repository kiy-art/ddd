import type { Metadata } from "next";
import Link from "next/link";

import FadeIn from "@/components/FadeIn";
import ProductCard from "@/components/ProductCard";
import { CATEGORIES, CATEGORY_LABELS, Product, getProducts } from "@/lib/api";

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

export default async function PopularPage() {
  let products: Product[] = [];
  let error: string | null = null;
  try {
    products = await getProducts({ limit: 200 });
  } catch {
    error = "商品情報の取得に失敗しました。しばらくしてから再度お試しください。";
  }

  const ranked = products.filter((p) => p.popularity_rank !== null);
  const popularAndDropping = ranked
    .filter(isPriceDropping)
    .sort((a, b) => (a.popularity_rank ?? 999) - (b.popularity_rank ?? 999));

  const byCategory = CATEGORIES.map((c) => ({
    category: c,
    products: ranked.filter((p) => p.category === c).sort((a, b) => (a.popularity_rank ?? 999) - (b.popularity_rank ?? 999)),
  })).filter((g) => g.products.length > 0);

  return (
    <div>
      <section className="bg-ink px-6 py-20 text-white sm:py-28">
        <div className="mx-auto max-w-7xl">
          <span className="text-xs font-medium uppercase tracking-[0.3em] text-accent">Popular</span>
          <h1 className="mt-3 font-display text-4xl font-semibold leading-tight sm:text-5xl">人気ランキング</h1>
          <p className="mt-3 max-w-xl text-sm text-white/70">
            楽天市場の実際のカテゴリ別売れ筋ランキングをもとにしています。当サイト独自の推測ではありません。
          </p>
        </div>
      </section>

      {error && (
        <div className="mx-auto max-w-7xl px-6 py-16">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}

      {!error && popularAndDropping.length > 0 && (
        <section className="border-b border-border px-6 py-16 sm:py-20">
          <div className="mx-auto max-w-7xl">
            <FadeIn className="flex flex-col gap-3">
              <span className="text-xs font-medium uppercase tracking-[0.3em] text-sale">🔥 Popular &amp; Dropping</span>
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
            現在、楽天市場の売れ筋ランキングに入っている商品はありません。ランキングは毎日更新されます。
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
