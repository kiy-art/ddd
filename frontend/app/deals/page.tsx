import type { Metadata } from "next";

import FadeIn from "@/components/FadeIn";
import PageHeader from "@/components/PageHeader";
import ProductCard from "@/components/ProductCard";
import { Product, getProducts } from "@/lib/api";
import { computeDeals } from "@/lib/deals";

export const revalidate = 0;

export const metadata: Metadata = {
  title: "価格が下がった商品",
  description: "直近の価格更新で値下がりした商品の一覧です。",
};

export default async function DealsPage() {
  let products: Product[] = [];
  try {
    products = await getProducts();
  } catch {
    products = [];
  }

  const deals = computeDeals(products);

  return (
    <div>
      <PageHeader
        eyebrow="Price Drops"
        title="価格が下がった商品"
        description={`直近の価格更新で値下がりした${deals.length}商品です。すべて実際に記録された値下がりのみを掲載しています。`}
        collageImages={deals.map(({ product }) => product.image_url)}
      />

      <section className="px-6 py-16 sm:py-20">
        <div className="mx-auto max-w-7xl">
          {deals.length === 0 ? (
            <p className="rounded-2xl border border-dashed border-border bg-card px-4 py-16 text-center text-sm text-foreground/50">
              現在、直近の更新で値下がりした商品はありません。
            </p>
          ) : (
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {deals.map(({ product, dropPercent }, i) => (
                <FadeIn key={product.id} delay={(i % 6) * 60} className="flex flex-col gap-2">
                  <span className="px-1 text-xs font-semibold text-brand dark:text-brand-light">
                    前回価格より {dropPercent}% 値下がり
                  </span>
                  <ProductCard product={product} listSource="deals" />
                </FadeIn>
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
