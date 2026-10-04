import type { Metadata } from "next";
import Link from "next/link";

import CompareTable from "@/components/CompareTable";
import PageHeader from "@/components/PageHeader";
import { ProductDetail, getProduct } from "@/lib/api";
import { MAX_COMPARE } from "@/lib/compare";
import PrNotice from "@/components/PrNotice";

export const revalidate = 0;


export const metadata: Metadata = {
  title: "商品比較",
  description: "選択したゴルフ用品を価格・買い時スコア・価格予測で比較できます。",
};

async function loadProducts(slugs: string[]): Promise<ProductDetail[]> {
  const results = await Promise.allSettled(slugs.map((slug) => getProduct(slug)));
  return results
    .filter((r): r is PromiseFulfilledResult<ProductDetail> => r.status === "fulfilled")
    .map((r) => r.value);
}

export default async function ComparePage({
  searchParams,
}: {
  searchParams: Promise<{ slugs?: string }>;
}) {
  const { slugs: slugsParam } = await searchParams;
  const slugs = (slugsParam ?? "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean)
    .slice(0, MAX_COMPARE);

  const products = slugs.length > 0 ? await loadProducts(slugs) : [];

  return (
    <div>
      <PageHeader
        eyebrow="Compare"
        title="商品比較"
        description={`価格・買い時スコア・価格予測を並べて比較できます（最大${MAX_COMPARE}商品）。`}
        collageImages={products.map((p) => p.image_url)}
      />

      <section className="px-6 py-16 sm:py-20">
        <div className="mx-auto max-w-7xl">
          {products.length < 2 ? (
            <div className="rounded-2xl border border-dashed border-border bg-card px-6 py-16 text-center">
              <p className="text-sm text-foreground/60">
                比較するには2商品以上が必要です。各商品ページやカードの「＋比較」ボタンから追加してください。
              </p>
              <Link
                href="/"
                className="mt-6 inline-block rounded-full bg-brand px-6 py-3 text-sm font-semibold text-on-brand transition-transform hover:scale-[1.02]"
              >
                商品を探す →
              </Link>
            </div>
          ) : (
            <div>
            <PrNotice className="mb-6" />
            <CompareTable products={products} removable />
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
