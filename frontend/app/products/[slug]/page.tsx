import type { Metadata } from "next";
import Image from "next/image";
import { notFound } from "next/navigation";

import BuyStatusBadge from "@/components/BuyStatusBadge";
import PriceHistoryChart from "@/components/PriceHistoryChart";
import { CATEGORY_LABELS, getProduct } from "@/lib/api";

export const revalidate = 0;

type Params = { slug: string };

function yen(value: number | null): string {
  if (value === null) return "-";
  return `¥${value.toLocaleString("ja-JP")}`;
}

async function loadProduct(slug: string) {
  try {
    return await getProduct(slug);
  } catch {
    return null;
  }
}

export async function generateMetadata({ params }: { params: Promise<Params> }): Promise<Metadata> {
  const { slug } = await params;
  const product = await loadProduct(slug);
  if (!product) return {};
  const title = product.ai_title || `${product.name} の価格推移と買い時判定`;
  return {
    title: `${title} | ゴルフ買い時ナビ`,
    description: product.ai_summary || product.buy_reason || product.name,
  };
}

export default async function ProductPage({ params }: { params: Promise<Params> }) {
  const { slug } = await params;
  const product = await loadProduct(slug);
  if (!product) notFound();

  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Product",
    name: product.name,
    brand: { "@type": "Brand", name: product.brand },
    ...(product.model_number ? { mpn: product.model_number } : {}),
    ...(product.image_url ? { image: [product.image_url] } : {}),
    url: `${siteUrl}/products/${product.slug}`,
    ...(product.current_price !== null
      ? {
          offers: {
            "@type": "Offer",
            priceCurrency: "JPY",
            price: product.current_price,
            availability: "https://schema.org/InStock",
            url: product.affiliate_url || product.product_url || `${siteUrl}/products/${product.slug}`,
          },
        }
      : {}),
  };

  return (
    <article className="flex flex-col gap-8">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <div className="grid grid-cols-1 gap-8 md:grid-cols-2">
        <div className="relative aspect-square w-full overflow-hidden rounded-xl bg-white dark:bg-zinc-900">
          {product.image_url ? (
            <Image
              src={product.image_url}
              alt={product.name}
              fill
              unoptimized
              className="object-contain p-6"
            />
          ) : (
            <div className="flex h-full items-center justify-center text-sm text-zinc-400">No Image</div>
          )}
        </div>

        <div className="flex flex-col gap-4">
          <span className="text-sm text-zinc-500">
            {CATEGORY_LABELS[product.category] ?? product.category} ・ {product.brand}
          </span>
          <h1 className="text-2xl font-bold">{product.ai_title || product.name}</h1>
          <div className="flex items-center gap-3">
            <BuyStatusBadge buyScore={product.buy_score} />
            {product.price_change_percent !== null && (
              <span
                className={`text-sm font-semibold ${
                  product.price_change_percent < 0 ? "text-red-600" : "text-zinc-500"
                }`}
              >
                {product.price_change_percent > 0 ? "+" : ""}
                {product.price_change_percent}% (30日平均比)
              </span>
            )}
          </div>

          <div className="rounded-xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
            <div className="text-3xl font-bold">{yen(product.current_price)}</div>
            <dl className="mt-2 grid grid-cols-3 gap-2 text-xs text-zinc-500">
              <div>
                <dt>過去30日平均</dt>
                <dd className="font-medium text-zinc-700 dark:text-zinc-300">{yen(product.average_price)}</dd>
              </div>
              <div>
                <dt>過去最安値</dt>
                <dd className="font-medium text-zinc-700 dark:text-zinc-300">{yen(product.lowest_price)}</dd>
              </div>
              <div>
                <dt>前回価格</dt>
                <dd className="font-medium text-zinc-700 dark:text-zinc-300">{yen(product.previous_price)}</dd>
              </div>
            </dl>
          </div>

          {product.buy_reason && (
            <div>
              <h2 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300">買い時の理由</h2>
              <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">{product.buy_reason}</p>
            </div>
          )}

          {product.ai_summary && (
            <div>
              <h2 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300">概要</h2>
              <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">{product.ai_summary}</p>
            </div>
          )}

          <div className="flex flex-col gap-2 sm:flex-row">
            {product.affiliate_url && (
              <a
                href={product.affiliate_url}
                target="_blank"
                rel="noopener noreferrer sponsored"
                className="flex-1 rounded-lg bg-orange-600 px-4 py-3 text-center text-sm font-semibold text-white hover:bg-orange-700"
              >
                購入ページを見る（広告・PR）
              </a>
            )}
            {product.product_url && (
              <a
                href={product.product_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex-1 rounded-lg border border-zinc-300 px-4 py-3 text-center text-sm font-semibold text-zinc-700 hover:bg-zinc-100 dark:border-zinc-700 dark:text-zinc-200 dark:hover:bg-zinc-800"
              >
                商品ページを見る
              </a>
            )}
          </div>
          {product.affiliate_url && (
            <p className="text-xs text-zinc-400">
              ※上記リンクにはアフィリエイトリンクが含まれます。リンク経由の購入により当サイトが紹介料を受け取る場合があります。
            </p>
          )}
        </div>
      </div>

      <section>
        <h2 className="mb-3 text-lg font-semibold">価格推移</h2>
        <PriceHistoryChart history={product.price_history} />
      </section>

      {product.ai_caution && (
        <p className="rounded-lg bg-zinc-100 p-3 text-xs text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400">
          ⚠ {product.ai_caution}
        </p>
      )}
    </article>
  );
}
