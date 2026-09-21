import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import CategoryGuide from "@/components/CategoryGuide";
import FadeIn from "@/components/FadeIn";
import ProductCard from "@/components/ProductCard";
import { CATEGORIES, CATEGORY_LABELS, Product, getCategoryProducts } from "@/lib/api";
import { GUIDES } from "@/lib/guides";

export const revalidate = 0;

type Params = { category: string };

const SORT_OPTIONS = ["discount", "signal", "price_asc"] as const;
type SortOption = (typeof SORT_OPTIONS)[number];

const SORT_LABELS: Record<SortOption, string> = {
  discount: "値下がり幅順",
  signal: "買い時順",
  price_asc: "価格が安い順",
};

function isSortOption(value: string | undefined): value is SortOption {
  return !!value && (SORT_OPTIONS as readonly string[]).includes(value);
}

function sortProducts(products: Product[], sort: SortOption): Product[] {
  const list = [...products];
  if (sort === "signal") {
    return list.sort((a, b) => (b.buy_signal_score ?? -1) - (a.buy_signal_score ?? -1));
  }
  if (sort === "price_asc") {
    return list.sort((a, b) => (a.current_price ?? Infinity) - (b.current_price ?? Infinity));
  }
  // "discount": already the API's default order (price_change_percent ascending), kept as-is
  return list;
}

export function generateStaticParams() {
  return CATEGORIES.map((category) => ({ category }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<Params>;
}): Promise<Metadata> {
  const { category } = await params;
  const label = CATEGORY_LABELS[category];
  if (!label) return {};
  return {
    title: `${label}の買い時商品一覧`,
    description: `${label}の価格推移と買い時判定を一覧で確認できます。`,
  };
}

export default async function CategoryPage({
  params,
  searchParams,
}: {
  params: Promise<Params>;
  searchParams: Promise<{ sort?: string }>;
}) {
  const { category } = await params;
  if (!CATEGORIES.includes(category as (typeof CATEGORIES)[number])) {
    notFound();
  }
  const { sort: sortParam } = await searchParams;
  const sort: SortOption = isSortOption(sortParam) ? sortParam : "discount";

  let products = [] as Product[];
  try {
    products = await getCategoryProducts(category);
  } catch {
    notFound();
  }

  const sortedProducts = sortProducts(products, sort);

  const droppedRecently = products.filter(
    (p) => p.current_price !== null && p.previous_price !== null && p.current_price < p.previous_price
  ).length;
  const cheapestVsAverage = products.length > 0 ? products[0] : null; // API default order = biggest discount first
  const relatedGuides = GUIDES.filter((g) => g.relatedCategories?.includes(category));

  return (
    <div>
      <section className="bg-brand px-6 py-20 text-white sm:py-28">
        <div className="mx-auto max-w-7xl">
          <span className="text-xs font-medium uppercase tracking-[0.3em] text-accent">Category</span>
          <h1 className="mt-3 font-display text-4xl font-semibold leading-tight sm:text-5xl">
            {CATEGORY_LABELS[category]}
          </h1>

          <dl className="mt-8 flex flex-wrap gap-x-12 gap-y-6 border-t border-white/15 pt-8">
            <div>
              <dt className="text-xs uppercase tracking-widest text-white/50">監視中のモデル</dt>
              <dd className="font-display text-3xl font-semibold">{products.length}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-widest text-white/50">直近で値下がりしたモデル</dt>
              <dd className="font-display text-3xl font-semibold">{droppedRecently}</dd>
            </div>
            {cheapestVsAverage?.price_change_percent !== undefined && cheapestVsAverage?.price_change_percent !== null && (
              <div>
                <dt className="text-xs uppercase tracking-widest text-white/50">30日平均から最も安いモデル</dt>
                <dd className="font-display text-lg font-semibold leading-snug">
                  {cheapestVsAverage.name}
                  <span className="ml-2 text-sm font-medium text-white/70">
                    {cheapestVsAverage.price_change_percent}%
                  </span>
                </dd>
              </div>
            )}
          </dl>
        </div>
      </section>

      <section className="px-6 py-16 sm:py-20">
        <div className="mx-auto max-w-7xl">
          {products.length === 0 ? (
            <p className="rounded-2xl border border-dashed border-border bg-card px-4 py-16 text-center text-sm text-foreground/50">
              現在このカテゴリで表示できる商品がありません。
            </p>
          ) : (
            <>
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs text-foreground/45">並び替え:</span>
                {SORT_OPTIONS.map((opt) => (
                  <Link
                    key={opt}
                    href={opt === "discount" ? `/category/${category}` : `/category/${category}?sort=${opt}`}
                    className={`rounded-full border px-3.5 py-1.5 text-xs font-semibold transition-colors ${
                      sort === opt
                        ? "border-brand bg-brand text-white"
                        : "border-border bg-background text-foreground/60 hover:border-brand/40 hover:text-brand dark:hover:text-brand-light"
                    }`}
                  >
                    {SORT_LABELS[opt]}
                  </Link>
                ))}
              </div>

              <div className="mt-8 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
                {sortedProducts.map((product, i) => (
                  <FadeIn key={product.id} delay={(i % 6) * 60}>
                    <ProductCard product={product} listSource="category" />
                  </FadeIn>
                ))}
              </div>
            </>
          )}
        </div>
      </section>

      <section className="border-t border-border px-6 py-16 sm:py-20">
        <div className="mx-auto max-w-7xl">
          <span className="text-xs font-medium uppercase tracking-[0.3em] text-accent">Buying Guide</span>
          <h2 className="mt-2 font-display text-2xl font-semibold text-foreground">
            {CATEGORY_LABELS[category]}の選び方
          </h2>
          <div className="mt-8">
            <CategoryGuide category={category} />
          </div>

          {relatedGuides.length > 0 && (
            <div className="mt-10 flex flex-wrap gap-3">
              {relatedGuides.map((guide) => (
                <Link
                  key={guide.slug}
                  href={`/guides/${guide.slug}`}
                  className="rounded-full border border-border px-4 py-2 text-sm text-foreground/70 transition-colors hover:border-foreground/30 hover:text-foreground"
                >
                  {guide.title} →
                </Link>
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
