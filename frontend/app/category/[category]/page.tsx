import type { Metadata } from "next";
import { notFound } from "next/navigation";

import FadeIn from "@/components/FadeIn";
import ProductCard from "@/components/ProductCard";
import { CATEGORIES, CATEGORY_LABELS, getCategoryProducts } from "@/lib/api";

export const revalidate = 0;

type Params = { category: string };

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

export default async function CategoryPage({ params }: { params: Promise<Params> }) {
  const { category } = await params;
  if (!CATEGORIES.includes(category as (typeof CATEGORIES)[number])) {
    notFound();
  }

  let products = [] as Awaited<ReturnType<typeof getCategoryProducts>>;
  try {
    products = await getCategoryProducts(category);
  } catch {
    notFound();
  }

  return (
    <div>
      <section className="bg-brand px-6 py-20 text-white sm:py-28">
        <div className="mx-auto max-w-7xl">
          <span className="text-xs font-medium uppercase tracking-[0.3em] text-accent">Category</span>
          <h1 className="mt-3 font-display text-4xl font-semibold leading-tight sm:text-5xl">
            {CATEGORY_LABELS[category]}
          </h1>
          <p className="mt-3 text-sm text-white/70">
            {products.length}商品の価格を分析中
          </p>
        </div>
      </section>

      <section className="px-6 py-16 sm:py-20">
        <div className="mx-auto max-w-7xl">
          {products.length === 0 ? (
            <p className="rounded-2xl border border-dashed border-border bg-card px-4 py-16 text-center text-sm text-foreground/50">
              現在このカテゴリで表示できる商品がありません。
            </p>
          ) : (
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {products.map((product, i) => (
                <FadeIn key={product.id} delay={(i % 6) * 60}>
                  <ProductCard product={product} />
                </FadeIn>
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
