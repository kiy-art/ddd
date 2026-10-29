import type { Metadata } from "next";

import FadeIn from "@/components/FadeIn";
import PageHeader from "@/components/PageHeader";
import ProductCard from "@/components/ProductCard";
import { Product, getProducts } from "@/lib/api";
import { computeDeals, dropLabel } from "@/lib/deals";
import PrNotice from "@/components/PrNotice";

export const revalidate = 0;

export const metadata: Metadata = {
  title: "価格が下がった商品",
  alternates: { canonical: "/deals" },
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
        eyebrow="値下がり"
        tone="drop"
        title="価格が下がった商品"
        description={`直近の価格更新で値下がりした${deals.length}商品です。当サイトが記録した「前回記録」との比較で、販売店・セット内容・クーポンが同じとは限りません。購入前に各販売店の最新価格をご確認ください。`}
        collageImages={deals.map(({ product }) => product.image_url)}
      />

      <section className="px-6 py-16 sm:py-20">
        <div className="mx-auto max-w-7xl">
          {deals.length === 0 ? (
            <p className="rounded-2xl border border-dashed border-border bg-card px-4 py-16 text-center text-sm text-foreground/50">
              現在、直近の更新で値下がりした商品はありません。
            </p>
          ) : (
            <div>
            <PrNotice className="mb-6" />
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {deals.map((deal, i) => {
                const { product } = deal;
                return (
                <FadeIn key={product.id} delay={(i % 6) * 60} className="flex flex-col gap-2">
                  <span className="self-start rounded-md bg-sale px-2 py-1 text-xs font-bold text-white">
                    {dropLabel(deal)}
                  </span>
                  <ProductCard product={product} listSource="deals" />
                </FadeIn>
                );
              })}
            </div>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
