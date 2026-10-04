import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import BrandFilterNav from "@/components/BrandFilterNav";
import CategoryGuide from "@/components/CategoryGuide";
import FadeIn from "@/components/FadeIn";
import PageHeader from "@/components/PageHeader";
import ProductCard from "@/components/ProductCard";
import { CATEGORIES, CATEGORY_LABELS, Product, getCategoryProducts } from "@/lib/api";
import { BRAND_PAGE_MIN_PRODUCTS, brandCategoryHref, brandCounts, brandSlug } from "@/lib/brandFilter";
import { pairHref } from "@/lib/comparePairs";
import { SORT_LABELS, SORT_OPTIONS, type SortOption, isSortOption, sortProducts } from "@/lib/productSort";
import { SITE_URL } from "@/lib/siteUrl";
import PrNotice from "@/components/PrNotice";

// STEP69: one page per maker within a category ("PING ドライバー") - a
// real search phrase the plain category page can't rank for. Everything
// on it comes from the products PAR. tracks: count, price range, how many
// are cheaper than last time, the products themselves.

export const revalidate = 0;

type Params = { category: string; brand: string };

function yen(value: number): string {
  return `¥${value.toLocaleString("ja-JP")}`;
}

async function load(category: string, slug: string) {
  if (!CATEGORIES.includes(category as (typeof CATEGORIES)[number])) return null;
  let all: Product[];
  try {
    all = await getCategoryProducts(category);
  } catch {
    return null;
  }
  const products = all.filter((p) => brandSlug(p.brand) === slug);
  if (products.length === 0) return null;
  return { all, products, brand: products[0].brand };
}

function facts(products: Product[]) {
  const prices = products.map((p) => p.current_price).filter((v): v is number => v !== null);
  const dropping = products.filter(
    (p) => p.current_price !== null && p.previous_price !== null && p.current_price < p.previous_price
  );
  const cheapest = [...products]
    .filter((p) => p.current_price !== null)
    .sort((a, b) => (a.current_price as number) - (b.current_price as number))[0];
  return {
    min: prices.length ? Math.min(...prices) : null,
    max: prices.length ? Math.max(...prices) : null,
    dropping: dropping.length,
    cheapest: cheapest ?? null,
  };
}

export async function generateMetadata({ params }: { params: Promise<Params> }): Promise<Metadata> {
  const { category, brand: slug } = await params;
  const data = await load(category, slug);
  if (!data) return {};
  const label = CATEGORY_LABELS[category] ?? category;
  const { min, max } = facts(data.products);
  const n = data.products.length;
  const url = `${SITE_URL}${brandCategoryHref(category, data.brand)}`;
  const title = `${data.brand}の${label}の価格比較・買い時｜${n}モデルの最安値と価格推移`;
  const range = min !== null && max !== null ? (min === max ? `現在${yen(min)}。` : `現在${yen(min)}〜${yen(max)}。`) : "";
  const description = `${data.brand}の${label}${n}モデルの価格を楽天市場・Yahoo!ショッピングで毎日比較。${range}過去の価格推移から、今が買い時かをAIが判定します。`;
  return {
    title,
    description,
    alternates: { canonical: url },
    // A one-product page is too thin to compete as its own result.
    robots: n >= BRAND_PAGE_MIN_PRODUCTS ? undefined : { index: false, follow: true },
    openGraph: { type: "website", url, title: `${title} - PAR.`, description },
    twitter: { card: "summary_large_image", title: `${title} - PAR.`, description },
  };
}

export default async function BrandCategoryPage({
  params,
  searchParams,
}: {
  params: Promise<Params>;
  searchParams: Promise<{ sort?: string }>;
}) {
  const { category, brand: slug } = await params;
  const data = await load(category, slug);
  if (!data) notFound();
  const { sort: sortParam } = await searchParams;
  const sort: SortOption = isSortOption(sortParam) ? sortParam : "discount";

  const label = CATEGORY_LABELS[category] ?? category;
  const { all, products, brand } = data;
  const { min, max, dropping, cheapest } = facts(products);
  const sorted = sortProducts(products, sort);
  const brands = brandCounts(all);

  // Real rival pairs for the comparison pages (STEP69 ④): this maker's
  // cheapest model against the closest-priced model of another maker.
  const rival =
    cheapest && cheapest.current_price !== null
      ? all
          .filter((p) => p.brand !== brand && p.current_price !== null)
          .sort(
            (a, b) =>
              Math.abs((a.current_price as number) - (cheapest.current_price as number)) -
              Math.abs((b.current_price as number) - (cheapest.current_price as number))
          )[0] ?? null
      : null;

  const pageUrl = `${SITE_URL}${brandCategoryHref(category, brand)}`;
  const jsonLd = [
    {
      "@context": "https://schema.org",
      "@type": "BreadcrumbList",
      itemListElement: [
        { "@type": "ListItem", position: 1, name: "ホーム", item: SITE_URL },
        { "@type": "ListItem", position: 2, name: label, item: `${SITE_URL}/category/${category}` },
        { "@type": "ListItem", position: 3, name: `${brand}の${label}`, item: pageUrl },
      ],
    },
    {
      "@context": "https://schema.org",
      "@type": "ItemList",
      itemListElement: sorted.map((p, i) => ({
        "@type": "ListItem",
        position: i + 1,
        url: `${SITE_URL}/products/${p.slug}`,
        name: p.name,
      })),
    },
  ];

  const summary =
    min !== null && max !== null
      ? `${brand}の${label}${products.length}モデルを毎日追跡中。現在の価格は${min === max ? yen(min) : `${yen(min)}〜${yen(max)}`}${
          dropping > 0 ? `、前回より値下がりしたモデルが${dropping}つあります` : ""
        }。`
      : `${brand}の${label}${products.length}モデルを追跡中です。`;

  return (
    <div>
      {jsonLd.map((block, i) => (
        <script key={i} type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(block) }} />
      ))}
      <PageHeader
        eyebrow={`${label} / ${brand}`}
        title={`${brand}の${label} 価格比較・買い時`}
        description={summary}
        collageImages={products.map((p) => p.image_url)}
      >
        <nav aria-label="パンくずリスト" className="mt-6 text-xs text-foreground/45">
          <Link href="/" className="hover:text-brand">ホーム</Link>
          <span className="mx-1.5">›</span>
          <Link href={`/category/${category}`} className="hover:text-brand">{label}</Link>
          <span className="mx-1.5">›</span>
          <span className="text-foreground/70">{brand}</span>
        </nav>
      </PageHeader>

      <section className="px-6 py-12 sm:py-16">
        <div className="mx-auto max-w-7xl">
          <dl className="mb-8 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Fact label="掲載モデル数" value={`${products.length}`} />
            <Fact label="最安モデルの価格" value={min !== null ? yen(min) : "—"} />
            <Fact label="最高価格" value={max !== null ? yen(max) : "—"} />
            <Fact label="前回より値下がり" value={`${dropping}モデル`} />
          </dl>

          <BrandFilterNav category={category} brands={brands} activeBrand={brand} totalCount={all.length} sort={sort} />

          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs text-foreground/45">並び替え:</span>
            {SORT_OPTIONS.map((opt) => (
              <Link
                key={opt}
                href={brandCategoryHref(category, brand, opt)}
                scroll={false}
                className={`rounded-full border px-3.5 py-1.5 text-xs font-semibold transition-colors ${
                  sort === opt
                    ? "border-brand bg-brand text-on-brand"
                    : "border-border bg-background text-foreground/60 hover:border-brand/40 hover:text-brand"
                }`}
              >
                {SORT_LABELS[opt]}
              </Link>
            ))}
          </div>

          <PrNotice className="mt-6" />
          <div className="mt-8 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {sorted.map((product, i) => (
              <FadeIn key={product.id} delay={(i % 6) * 60}>
                <ProductCard product={product} listSource="brand_category" />
              </FadeIn>
            ))}
          </div>

          <div className="mt-10 flex flex-wrap gap-3 text-sm">
            <Link
              href={`/brand/${encodeURIComponent(brand)}`}
              className="rounded-full border border-border px-4 py-2 text-foreground/70 hover:border-brand/40 hover:text-brand"
            >
              {brand}の全カテゴリを見る →
            </Link>
            {cheapest && rival && (
              <Link
                href={pairHref(cheapest.slug, rival.slug)}
                className="rounded-full border border-border px-4 py-2 text-foreground/70 hover:border-brand/40 hover:text-brand"
              >
                {cheapest.name} と {rival.brand} {rival.name} を比較 →
              </Link>
            )}
          </div>
        </div>
      </section>

      <section className="border-t border-border px-6 py-16 sm:py-20">
        <div className="mx-auto max-w-7xl">
          <span className="text-xs font-medium uppercase tracking-[0.3em] text-accent">Buying Guide</span>
          <h2 className="mt-2 font-display text-2xl font-semibold text-foreground">{label}の選び方</h2>
          <div className="mt-8">
            <CategoryGuide category={category} />
          </div>
        </div>
      </section>
    </div>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-border bg-card px-4 py-3">
      <dt className="text-[11px] text-foreground/45">{label}</dt>
      <dd className="mt-1 font-num text-lg font-semibold text-foreground">{value}</dd>
    </div>
  );
}
