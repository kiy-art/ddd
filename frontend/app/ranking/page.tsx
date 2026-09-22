import type { Metadata } from "next";
import Link from "next/link";

import AiBuySignal from "@/components/AiBuySignal";
import FadeIn from "@/components/FadeIn";
import { CATEGORIES, CATEGORY_LABELS, Product, getCategoryProducts } from "@/lib/api";

export const revalidate = 0;

export const metadata: Metadata = {
  title: "買い時ランキング",
  description: "カテゴリ別のPAR. BUY SIGNALランキングです。",
};

function isCategory(value: string | undefined): value is (typeof CATEGORIES)[number] {
  return !!value && (CATEGORIES as readonly string[]).includes(value);
}

function yen(value: number | null): string {
  if (value === null) return "-";
  return `¥${value.toLocaleString("ja-JP")}`;
}

export default async function RankingPage({
  searchParams,
}: {
  searchParams: Promise<{ category?: string }>;
}) {
  const { category: categoryParam } = await searchParams;
  const category = isCategory(categoryParam) ? categoryParam : CATEGORIES[0];

  let products: Product[] = [];
  try {
    products = await getCategoryProducts(category);
  } catch {
    products = [];
  }

  const ranked = [...products].sort((a, b) => (b.buy_signal_score ?? -1) - (a.buy_signal_score ?? -1));

  return (
    <div>
      <section className="bg-ink px-6 py-20 text-white sm:py-28">
        <div className="mx-auto max-w-7xl">
          <span className="text-xs font-medium uppercase tracking-[0.3em] text-accent">Ranking</span>
          <h1 className="mt-3 font-display text-4xl font-semibold leading-tight sm:text-5xl">買い時ランキング</h1>
          <p className="mt-3 text-sm text-white/70">PAR. BUY SIGNALが高い順に並べたカテゴリ別ランキングです。</p>
        </div>
      </section>

      <section className="px-6 py-16 sm:py-20">
        <div className="mx-auto max-w-7xl">
          <div className="flex flex-wrap gap-2">
            {CATEGORIES.map((c) => (
              <Link
                key={c}
                href={`/ranking?category=${c}`}
                className={`rounded-full border px-3.5 py-1.5 text-xs font-semibold transition-colors ${
                  category === c
                    ? "border-brand bg-brand text-white"
                    : "border-border bg-background text-foreground/60 hover:border-brand/40 hover:text-brand dark:hover:text-brand-light"
                }`}
              >
                {CATEGORY_LABELS[c]}
              </Link>
            ))}
          </div>

          {ranked.length === 0 ? (
            <p className="mt-12 rounded-2xl border border-dashed border-border bg-card px-4 py-16 text-center text-sm text-foreground/50">
              現在このカテゴリで表示できる商品がありません。
            </p>
          ) : (
            <ol className="mt-8 flex flex-col gap-3">
              {ranked.map((product, i) => (
                <FadeIn key={product.id} delay={(i % 8) * 50}>
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
          )}
        </div>
      </section>
    </div>
  );
}
