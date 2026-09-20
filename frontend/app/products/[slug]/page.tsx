import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import AiBuySignal from "@/components/AiBuySignal";
import CategoryIcon from "@/components/CategoryIcon";
import FadeIn from "@/components/FadeIn";
import MonthlyTrendChart from "@/components/MonthlyTrendChart";
import PriceHistoryChart from "@/components/PriceHistoryChart";
import SafeProductImage from "@/components/SafeProductImage";
import SeasonalTrend from "@/components/SeasonalTrend";
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
    title,
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
    <article>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />

      <div className="border-b border-border bg-card">
        <div className="mx-auto max-w-7xl px-6 py-8">
          <Link href={`/category/${product.category}`} className="text-xs font-medium uppercase tracking-widest text-foreground/40 hover:text-brand">
            ← {CATEGORY_LABELS[product.category] ?? product.category}
          </Link>
        </div>
      </div>

      <div className="mx-auto max-w-7xl px-6 py-12 sm:py-16">
        <div className="grid grid-cols-1 gap-12 lg:grid-cols-2 lg:gap-16">
          <FadeIn className="relative aspect-square w-full overflow-hidden rounded-2xl border border-border bg-card">
            {product.image_url ? (
              <SafeProductImage
                src={product.image_url}
                alt={product.name}
                category={product.category}
                className="object-contain p-10"
              />
            ) : (
              <CategoryIcon category={product.category} />
            )}
          </FadeIn>

          <FadeIn delay={100} className="flex flex-col gap-6">
            <div>
              <span className="text-xs font-medium uppercase tracking-widest text-foreground/40">
                {product.brand}
              </span>
              <h1 className="mt-2 font-display text-3xl font-semibold leading-tight text-foreground sm:text-4xl">
                {product.name}
              </h1>
            </div>

            <div className="flex items-center gap-6 rounded-2xl border border-border bg-card p-6">
              <AiBuySignal buyScore={product.buy_score} priceChangePercent={product.price_change_percent} size="lg" />
              <div className="flex flex-col gap-1 border-l border-border pl-6">
                <span className="font-display text-4xl font-semibold text-foreground">
                  {yen(product.current_price)}
                </span>
                {product.price_change_percent !== null && (
                  <span
                    className={`text-sm font-semibold ${
                      product.price_change_percent < 0 ? "text-brand dark:text-brand-light" : "text-foreground/50"
                    }`}
                  >
                    {product.price_change_percent > 0 ? "+" : ""}
                    {product.price_change_percent}% vs 30日平均
                  </span>
                )}
              </div>
            </div>

            <dl className="grid grid-cols-3 gap-4 text-xs text-foreground/45">
              <div>
                <dt>過去30日平均</dt>
                <dd className="mt-1 font-display text-base font-medium text-foreground">{yen(product.average_price)}</dd>
              </div>
              <div>
                <dt>過去最安値</dt>
                <dd className="mt-1 font-display text-base font-medium text-foreground">{yen(product.lowest_price)}</dd>
              </div>
              <div>
                <dt>前回価格</dt>
                <dd className="mt-1 font-display text-base font-medium text-foreground">{yen(product.previous_price)}</dd>
              </div>
            </dl>

            <div className="flex flex-col gap-2 sm:flex-row">
              {product.affiliate_url && (
                <a
                  href={product.affiliate_url}
                  target="_blank"
                  rel="noopener noreferrer sponsored"
                  className="flex-1 rounded-full bg-brand px-6 py-4 text-center text-sm font-semibold text-white transition-transform hover:scale-[1.02]"
                >
                  購入ページを見る（広告・PR）
                </a>
              )}
              {product.product_url && (
                <a
                  href={product.product_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-1 rounded-full border border-border px-6 py-4 text-center text-sm font-semibold text-foreground/80 transition-colors hover:bg-background"
                >
                  商品ページを見る
                </a>
              )}
            </div>
            {product.affiliate_url && (
              <p className="text-xs text-foreground/35">
                ※上記リンクにはアフィリエイトリンクが含まれる場合があります。リンク経由の購入により当サイトが紹介料を受け取ることがあります。
              </p>
            )}
          </FadeIn>
        </div>

        <FadeIn className="mt-16 rounded-2xl border border-border bg-card p-6 sm:p-10">
          <span className="text-xs font-medium uppercase tracking-[0.3em] text-accent">Price History</span>
          <h2 className="mt-2 font-display text-2xl font-semibold text-foreground">直近の価格推移</h2>
          <div className="mt-8">
            <PriceHistoryChart history={product.price_history} />
          </div>
        </FadeIn>

        <FadeIn className="mt-10 rounded-2xl border border-border bg-card p-6 sm:p-10">
          <span className="text-xs font-medium uppercase tracking-[0.3em] text-accent">Long-Term Trend</span>
          <h2 className="mt-2 font-display text-2xl font-semibold text-foreground">長期価格推移（月次・最大3年）</h2>
          <div className="mt-8">
            <MonthlyTrendChart history={product.price_history} />
          </div>
        </FadeIn>

        <FadeIn className="mt-10">
          <SeasonalTrend category={product.category} />
        </FadeIn>

        {(product.buy_reason || product.ai_summary) && (
          <FadeIn className="mt-10 rounded-2xl bg-brand p-6 text-white sm:p-10">
            <span className="text-xs font-medium uppercase tracking-[0.3em] text-accent">Why AI Thinks This Is a Good Buy</span>
            <h2 className="mt-2 font-display text-2xl font-semibold">AIによる判定理由</h2>
            <div className="mt-5 flex flex-col gap-4 text-sm leading-relaxed text-white/80">
              {product.buy_reason && <p>{product.buy_reason}</p>}
              {product.ai_summary && <p>{product.ai_summary}</p>}
            </div>
          </FadeIn>
        )}

        {product.ai_caution && (
          <p className="mt-8 rounded-xl border border-border bg-card px-4 py-3 text-xs text-foreground/45">
            ⚠ {product.ai_caution}
          </p>
        )}
      </div>
    </article>
  );
}
