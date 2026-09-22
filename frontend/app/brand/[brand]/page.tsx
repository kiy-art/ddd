import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import FadeIn from "@/components/FadeIn";
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

  return (
    <div>
      <section className="bg-ink px-6 py-20 text-white sm:py-28">
        <div className="mx-auto max-w-7xl">
          <span className="text-xs font-medium uppercase tracking-[0.3em] text-accent">Brand</span>
          <h1 className="mt-3 font-display text-4xl font-semibold leading-tight sm:text-5xl">{name}</h1>
          <p className="mt-3 text-sm text-white/70">{products.length}商品の価格を分析中</p>

          {priceStats && priceStats.reliable_count > 0 ? (
            <dl className="mt-8 flex flex-wrap gap-x-12 gap-y-6 border-t border-white/15 pt-8">
              <div>
                <dt className="text-xs uppercase tracking-widest text-white/50">価格傾向を判定できた商品</dt>
                <dd className="font-display text-3xl font-semibold">
                  {priceStats.reliable_count}
                  <span className="ml-1 text-base font-normal text-white/50">/ {priceStats.tracked_count}</span>
                </dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-widest text-white/50">値下がり中 / 値上がり中</dt>
                <dd className="font-display text-3xl font-semibold">
                  {priceStats.declining_count}
                  <span className="mx-1 text-base font-normal text-white/50">/</span>
                  {priceStats.rising_count}
                </dd>
              </div>
              {priceStats.average_change_percent !== null && (
                <div>
                  <dt className="text-xs uppercase tracking-widest text-white/50">平均値動き（30日平均比）</dt>
                  <dd
                    className={`font-display text-3xl font-semibold ${
                      priceStats.average_change_percent < 0 ? "text-brand-light" : ""
                    }`}
                  >
                    {pct(priceStats.average_change_percent)}
                  </dd>
                </div>
              )}
              {priceStats.average_msrp_discount_percent !== null && (
                <div>
                  <dt className="text-xs uppercase tracking-widest text-white/50">定価からの平均乖離</dt>
                  <dd
                    className={`font-display text-3xl font-semibold ${
                      priceStats.average_msrp_discount_percent < 0 ? "text-brand-light" : ""
                    }`}
                  >
                    {pct(priceStats.average_msrp_discount_percent)}
                  </dd>
                </div>
              )}
              {priceStats.biggest_decline && (
                <div>
                  <dt className="text-xs uppercase tracking-widest text-white/50">最も値下がり中のモデル</dt>
                  <dd className="font-display text-lg font-semibold leading-snug">
                    <Link
                      href={`/products/${priceStats.biggest_decline.product_slug}`}
                      className="hover:text-accent"
                    >
                      {priceStats.biggest_decline.product_name}
                    </Link>
                    <span className="ml-2 text-sm font-medium text-white/70">
                      {pct(priceStats.biggest_decline.change_percent)}
                    </span>
                  </dd>
                </div>
              )}
            </dl>
          ) : (
            priceStats &&
            priceStats.tracked_count > 0 && (
              <p className="mt-8 border-t border-white/15 pt-8 text-sm text-white/50">
                価格データ蓄積中です。傾向を判定できる商品が増え次第、このブランドの値動きを表示します。
              </p>
            )
          )}
        </div>
      </section>

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
