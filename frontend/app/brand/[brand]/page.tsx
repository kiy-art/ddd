import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import FadeIn from "@/components/FadeIn";
import PageHeader from "@/components/PageHeader";
import ProductCard from "@/components/ProductCard";
import { BrandPriceStats, getBrandPriceStats, getBrandProducts } from "@/lib/api";

export const revalidate = 0;

type Params = { brand: string };

function pct(value: number): string {
  return `${value > 0 ? "+" : ""}${value}%`;
}

export async function generateMetadata({ params }: { params: Promise<Params> }): Promise<Metadata> {
  const { brand } = await params;
  const name = decodeURIComponent(brand);
  return {
    title: `${name}の買い時商品一覧`,
    description: `${name}の商品の価格推移と買い時判定を一覧で確認できます。`,
  };
}

export default async function BrandPage({ params }: { params: Promise<Params> }) {
  const { brand } = await params;
  const name = decodeURIComponent(brand);

  let products = [] as Awaited<ReturnType<typeof getBrandProducts>>;
  try {
    products = await getBrandProducts(name);
  } catch {
    notFound();
  }

  let priceStats: BrandPriceStats | null = null;
  try {
    priceStats = await getBrandPriceStats(name);
  } catch {
    priceStats = null;
  }

  const stats =
    priceStats && priceStats.reliable_count > 0
      ? [
          {
            label: "値下がり中 / 値上がり中",
            value: (
              <>
                {priceStats.declining_count}
                <span className="mx-1 text-base font-normal text-foreground/40">/</span>
                {priceStats.rising_count}
              </>
            ),
          },
          ...(priceStats.average_change_percent !== null
            ? [
                {
                  label: "平均価格の動き（30日平均比）",
                  value: (
                    <span className={priceStats.average_change_percent < 0 ? "text-brand dark:text-brand-light" : ""}>
                      {pct(priceStats.average_change_percent)}
                    </span>
                  ),
                },
              ]
            : []),
          ...(priceStats.average_msrp_discount_percent !== null
            ? [
                {
                  label: "定価との平均差",
                  value: (
                    <span
                      className={priceStats.average_msrp_discount_percent < 0 ? "text-brand dark:text-brand-light" : ""}
                    >
                      {pct(priceStats.average_msrp_discount_percent)}
                    </span>
                  ),
                },
              ]
            : []),
        ]
      : [];

  return (
    <div>
      <PageHeader
        eyebrow="Brand"
        title={name}
        description={`${products.length}商品の価格を毎日追跡しています。`}
        stats={stats}
        collageImages={products.map((p) => p.image_url)}
      >
        {priceStats && priceStats.reliable_count > 0 && priceStats.biggest_decline && (
          <div className="mt-8 rounded-2xl border border-border bg-background p-5">
            <span className="text-xs font-medium uppercase tracking-widest text-foreground/40">
              一番お得なモデル
            </span>
            <p className="mt-1.5 font-display text-lg font-semibold leading-snug text-foreground">
              <Link href={`/products/${priceStats.biggest_decline.product_slug}`} className="hover:text-brand">
                {priceStats.biggest_decline.product_name}
              </Link>
              <span className="ml-2 text-sm font-medium text-brand dark:text-brand-light">
                {pct(priceStats.biggest_decline.change_percent)}
              </span>
            </p>
          </div>
        )}
        {priceStats && priceStats.reliable_count === 0 && priceStats.tracked_count > 0 && (
          <p className="mt-8 border-t border-border pt-6 text-sm text-foreground/50">
            価格分析準備中です。データが揃い次第、このブランドの値動きを表示します。
          </p>
        )}
      </PageHeader>

      <section className="px-6 py-16 sm:py-20">
        <div className="mx-auto max-w-7xl">
          {products.length === 0 ? (
            <p className="rounded-2xl border border-dashed border-border bg-card px-4 py-16 text-center text-sm text-foreground/50">
              現在このブランドで表示できる商品がありません。
            </p>
          ) : (
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {products.map((product, i) => (
                <FadeIn key={product.id} delay={(i % 6) * 60}>
                  <ProductCard product={product} listSource="brand" />
                </FadeIn>
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
