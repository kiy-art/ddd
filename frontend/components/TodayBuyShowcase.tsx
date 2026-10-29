"use client";

import Link from "next/link";

import CtaArrow from "@/components/CtaArrow";
import SafeProductImage from "@/components/SafeProductImage";
import TrackedCta from "@/components/TrackedCta";
import { CATEGORY_LABELS, Product } from "@/lib/api";
import { trackEvent } from "@/lib/analytics";
import { comparePrice } from "@/lib/priceCopy";
import { shopOf } from "@/lib/shopRows";
import { displayName } from "@/lib/displayName";

// Same threshold as ProductCard: a "30日平均" claim needs real history.
const THIN_DATA_DAYS = 7;

function yen(value: number | null): string {
  if (value === null) return "-";
  return `¥${value.toLocaleString("ja-JP")}`;
}

// Top-of-page "今日の買い時": 1 large + 4 small cards, 2 columns on a phone.
// The comparison basis (定価比 preferred, else 30日平均比) and the price
// itself are exactly the ones ProductCard uses - nothing is invented here.
// Shop clicks are recorded with placement "home_top_pick" so they can be
// told apart from the "product_card" buttons further down the page.
export default function TodayBuyShowcase({ products }: { products: Product[] }) {
  if (products.length === 0) return null;
  const [lead, ...rest] = products;

  return (
    <div id="best-buy" className="grid scroll-mt-20 grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4 lg:grid-rows-2">
      <PickCard product={lead} large />
      {rest.slice(0, 4).map((p) => (
        <PickCard key={p.id} product={p} />
      ))}
    </div>
  );
}

function PickCard({ product, large = false }: { product: Product; large?: boolean }) {
  const hasReliableTrend = product.buy_score !== "insufficient_data" && product.history_span_days >= THIN_DATA_DAYS;
  const comparison =
    product.msrp !== null && product.current_price !== null
      ? comparePrice(product.current_price, product.msrp, "定価")
      : hasReliableTrend && product.average_price !== null && product.current_price !== null
        ? comparePrice(product.current_price, product.average_price, "30日平均")
        : null;
  const shop = product.affiliate_url ? shopOf(product.affiliate_url) : null;

  return (
    <article
      className={`card-lux flex flex-col overflow-hidden rounded-2xl bg-card ${
        large ? "col-span-2 lg:row-span-2" : ""
      }`}
    >
      <Link
        href={`/products/${product.slug}`}
        onClick={() =>
          trackEvent("product_card_click", {
            product_id: product.id,
            product_slug: product.slug,
            list_source: "homepage_top_pick",
          })
        }
        className="flex flex-1 flex-col"
      >
        <div className={`relative w-full bg-background ${large ? "aspect-[16/9] lg:aspect-[4/3]" : "aspect-[4/3]"}`}>
          <SafeProductImage
            src={product.image_url}
            alt={product.name}
            category={product.category}
            className="object-contain p-4"
          />
          {comparison && comparison.direction === "down" && (
            <span className="absolute left-2 top-2 z-10 rounded-full bg-sale px-2.5 py-1 text-[11px] font-bold text-white shadow-sm">
              {comparison.label}
            </span>
          )}
        </div>
        <div className={`flex flex-1 flex-col gap-1 ${large ? "p-4 sm:p-5" : "p-3"}`}>
          <span className="text-[11px] font-medium text-foreground/65">
            {CATEGORY_LABELS[product.category] ?? product.category} · {product.brand}
          </span>
          <h3
            className={`line-clamp-2 font-display font-bold leading-snug text-foreground ${
              large ? "text-base sm:text-lg" : "text-[13px] sm:text-sm"
            }`}
          >
            {displayName(product)}
          </h3>
          <p className={`mt-auto font-num font-semibold text-foreground ${large ? "text-2xl" : "text-lg"}`}>
            {yen(product.current_price)}
          </p>
          {comparison && comparison.direction !== "down" && (
            <p className="text-[11px] text-foreground/65">{comparison.label}</p>
          )}
        </div>
      </Link>
      {shop && product.affiliate_url && (
        <div className={large ? "px-4 pb-4 sm:px-5 sm:pb-5" : "px-3 pb-3"}>
          <TrackedCta
            href={product.affiliate_url}
            target="_blank"
            rel="noopener noreferrer sponsored"
            className="btn-shop tap inline-flex min-h-11 w-full items-center justify-center gap-1.5 whitespace-nowrap rounded-full px-3 py-2.5 text-[13px] font-semibold"
            event="cta_click"
            params={{
              product_id: product.id,
              product_slug: product.slug,
              product_name: product.name,
              cta_type: "affiliate",
              shop: shop.key,
              buy_score: product.buy_score,
              list_source: "homepage_top_pick",
            }}
            productId={product.id}
            category={product.category}
            placement="home_top_pick"
          >
            {shop.label}で見る
            <CtaArrow className="h-3.5 w-3.5" />
          </TrackedCta>
        </div>
      )}
    </article>
  );
}
