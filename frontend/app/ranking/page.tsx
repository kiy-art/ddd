import type { Metadata } from "next";
import Link from "next/link";

import AiBuySignal from "@/components/AiBuySignal";
import CategoryIcon from "@/components/CategoryIcon";
import FadeIn from "@/components/FadeIn";
import SafeProductImage from "@/components/SafeProductImage";
import { CATEGORIES, CATEGORY_LABELS, Product, getCategoryProducts } from "@/lib/api";
import { getProductBadge } from "@/lib/badges";

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

function ProductThumb({ product, className }: { product: Product; className?: string }) {
  return (
    <div className={`relative shrink-0 overflow-hidden rounded-xl bg-background ${className ?? ""}`}>
      {product.image_url ? (
        <SafeProductImage src={product.image_url} alt={product.name} category={product.category} className="object-contain p-3" />
      ) : (
        <CategoryIcon category={product.category} />
      )}
    </div>
  );
}

function FeaturedRankCard({ product }: { product: Product }) {
  const badge = getProductBadge(product);
  return (
    <Link
      href={`/products/${product.slug}`}
      className="group grid grid-cols-1 gap-8 overflow-hidden rounded-3xl border border-border bg-card p-6 transition-colors hover:border-brand/40 sm:grid-cols-[1fr_1.2fr] sm:p-10"
    >
      <div className="relative aspect-square w-full overflow-hidden rounded-2xl bg-background">
        <span
          aria-hidden="true"
          className="pointer-events-none absolute -left-3 -top-8 select-none font-display text-[180px] font-semibold leading-none text-foreground/[0.07] sm:text-[220px]"
        >
          01
        </span>
        {product.image_url ? (
          <SafeProductImage src={product.image_url} alt={product.name} category={product.category} className="object-contain p-8" />
        ) : (
          <CategoryIcon category={product.category} />
        )}
      </div>
      <div className="flex flex-col justify-center gap-4">
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-brand px-3 py-1 text-[10px] font-semibold uppercase tracking-widest text-white">
            No.1
          </span>
          {badge && (
            <span
              className={`rounded-full px-3 py-1 text-[10px] font-semibold uppercase tracking-widest ${
                badge.tone === "strong" ? "bg-brand text-white" : "bg-ink text-white"
              }`}
            >
              {badge.label}
            </span>
          )}
        </div>
        <div>
          <span className="text-xs font-medium uppercase tracking-widest text-foreground/40">{product.brand}</span>
          <h2 className="mt-1 font-display text-3xl font-semibold leading-tight text-foreground sm:text-4xl">
            {product.name}
          </h2>
        </div>
        <div className="flex items-end gap-6">
          <span className="font-display text-3xl font-semibold text-foreground">{yen(product.current_price)}</span>
          <AiBuySignal
            buyScore={product.buy_score}
            buySignalScore={product.buy_signal_score}
            historySpanDays={product.history_span_days}
            size="lg"
          />
        </div>
        <span className="w-fit text-sm font-semibold text-brand transition-transform group-hover:translate-x-1">
          詳細を見る →
        </span>
      </div>
    </Link>
  );
}

function MediumRankCard({ product, rank }: { product: Product; rank: number }) {
  return (
    <Link
      href={`/products/${product.slug}`}
      className="flex flex-col gap-4 rounded-2xl border border-border bg-card p-5 transition-colors hover:border-brand/40 sm:flex-row sm:items-center"
    >
      <span className="font-display text-4xl font-semibold text-foreground/15">{String(rank).padStart(2, "0")}</span>
      <ProductThumb product={product} className="aspect-square w-full sm:w-24" />
      <div className="min-w-0 flex-1">
        <span className="text-[11px] font-medium uppercase tracking-widest text-foreground/40">{product.brand}</span>
        <div className="truncate font-display text-base font-medium text-foreground">{product.name}</div>
        <div className="mt-1 font-display text-lg font-semibold text-foreground">{yen(product.current_price)}</div>
      </div>
      <AiBuySignal
        buyScore={product.buy_score}
        buySignalScore={product.buy_signal_score}
        historySpanDays={product.history_span_days}
        size="sm"
      />
    </Link>
  );
}

function CompactRankRow({ product, rank }: { product: Product; rank: number }) {
  return (
    <Link
      href={`/products/${product.slug}`}
      className="flex items-center gap-4 rounded-2xl border border-border bg-card p-4 transition-colors hover:border-brand/40 sm:p-5"
    >
      <span className="w-8 shrink-0 text-center font-display text-xl font-semibold text-foreground/25">{rank}</span>
      <ProductThumb product={product} className="aspect-square w-14" />
      <div className="min-w-0 flex-1">
        <span className="text-[11px] font-medium uppercase tracking-widest text-foreground/40">{product.brand}</span>
        <div className="truncate font-display text-base font-medium text-foreground">{product.name}</div>
        <div className="mt-1 text-sm text-foreground/50">{yen(product.current_price)}</div>
      </div>
      <AiBuySignal
        buyScore={product.buy_score}
        buySignalScore={product.buy_signal_score}
        historySpanDays={product.history_span_days}
        size="sm"
      />
    </Link>
  );
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
  const [first, ...rest] = ranked;
  const medium = rest.slice(0, 2);
  const compact = rest.slice(2);

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
            <div className="mt-8 flex flex-col gap-4">
              {first && (
                <FadeIn>
                  <FeaturedRankCard product={first} />
                </FadeIn>
              )}

              {medium.length > 0 && (
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  {medium.map((product, i) => (
                    <FadeIn key={product.id} delay={(i + 1) * 60}>
                      <MediumRankCard product={product} rank={i + 2} />
                    </FadeIn>
                  ))}
                </div>
              )}

              {compact.length > 0 && (
                <ol className="flex flex-col gap-3">
                  {compact.map((product, i) => (
                    <FadeIn key={product.id} delay={(i % 8) * 50}>
                      <CompactRankRow product={product} rank={i + 4} />
                    </FadeIn>
                  ))}
                </ol>
              )}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
