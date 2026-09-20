import type { Metadata } from "next";
import { notFound } from "next/navigation";

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
    title: `${label}の買い時商品一覧 | ゴルフ買い時ナビ`,
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
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold">{CATEGORY_LABELS[category]}の買い時商品</h1>

      {products.length === 0 && (
        <p className="text-sm text-zinc-500">現在このカテゴリで表示できる商品がありません。</p>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {products.map((product) => (
          <ProductCard key={product.id} product={product} />
        ))}
      </div>
    </div>
  );
}
