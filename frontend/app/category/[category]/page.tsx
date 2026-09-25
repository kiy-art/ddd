import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import CategoryGuide from "@/components/CategoryGuide";
import CuratedPickCard from "@/components/CuratedPickCard";
import FadeIn from "@/components/FadeIn";
import PageHeader from "@/components/PageHeader";
import ProductCard from "@/components/ProductCard";
import { CATEGORIES, CATEGORY_LABELS, Product, getCategoryProducts } from "@/lib/api";
import { curateTodaysPicks } from "@/lib/curatePicks";
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

  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";
  const url = `${siteUrl}/category/${category}`;
  // No manual "- PAR." suffix here: the root layout's title.template
  // ("%s | PAR.") already appends it to the <title> field. openGraph/
  // twitter titles aren't covered by that template, so they get it added
  // explicitly below.
  const title = `${label}の最安値・買い時ランキング｜価格推移を比較`;
  const description = `${label}の価格推移と過去最安値をもとに、今が買い時の${label}をAIが判定。値下がりしやすい時期の目安も掲載しています。`;
  const ogTitle = `${title} - PAR.`;

  return {
    title,
    description,
    alternates: { canonical: url },
    openGraph: { type: "website", url, title: ogTitle, description },
    twitter: { card: "summary_large_image", title: ogTitle, description },
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
  const relatedGuides = GUIDES.filter((g) => g.relatedCategories?.includes(category));
  const todaysPicks = curateTodaysPicks(products);
  const categoryLabel = CATEGORY_LABELS[category] ?? category;

  const summary =
    products.length === 0
      ? `現在、${categoryLabel}の価格データを準備中です。`
      : droppedRecently > 0
        ? `本日、値下がり中の${categoryLabel}が${droppedRecently}点あります。`
        : `${categoryLabel}を${products.length}点、毎日価格を追跡しています。`;

  return (
    <div>
      <PageHeader
        eyebrow="Category"
        title={`今日の${categoryLabel}お買い得情報`}
        description={summary}
        collageImages={products.map((p) => p.image_url)}
      >
        {todaysPicks.length > 0 && (
          <div className="mt-10 grid grid-cols-2 gap-4 sm:grid-cols-4">
            {todaysPicks.slice(0, 4).map((pick) => (
              <CuratedPickCard
                key={pick.product.id}
                label={pick.label}
                product={pick.product}
                listSource="category_today_pick"
              />
            ))}
          </div>
        )}
      </PageHeader>

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
