"use client";

import Link from "next/link";

import AiBuySignal from "@/components/AiBuySignal";
import CategoryIcon from "@/components/CategoryIcon";
import CompareButton from "@/components/CompareButton";
import FavoriteButton from "@/components/FavoriteButton";
import SafeProductImage from "@/components/SafeProductImage";
import { CATEGORY_LABELS, Product } from "@/lib/api";
import { trackEvent } from "@/lib/analytics";
import { getProductBadge } from "@/lib/badges";

// See app/products/[slug]/page.tsx for why this threshold exists: a
// "30-day average" claim needs more than a day or two of real data behind it.
const THIN_DATA_DAYS = 7;

// Even a legitimate discount this large is unusual enough to flag for a
// second look, rather than presenting it as an uncomplicated great deal.
const CAUTION_DISCOUNT_PERCENT = -40;

function yen(value: number | null): string {
  if (value === null) return "-";
  return `¥${value.toLocaleString("ja-JP")}`;
}

export default function ProductCard({ product, listSource }: { product: Product; listSource?: string }) {
  const hasReliableTrend = product.buy_score !== "insufficient_data" && product.history_span_days >= THIN_DATA_DAYS;
  const pct = hasReliableTrend ? product.price_change_percent : null;
  const badge = getProductBadge(product);

  return (
    <Link
      href={`/products/${product.slug}`}
      onClick={() =>
        trackEvent("product_card_click", {
          product_id: product.id,
          product_slug: product.slug,
          list_source: listSource ?? "unknown",
        })
      }
      className="group flex flex-col overflow-hidden rounded-2xl border border-border bg-card transition-all duration-300 hover:-translate-y-1 hover:shadow-[0_24px_48px_-24px_rgba(20,19,15,0.22)]"
    >
      <div className="relative aspect-[4/3] w-full bg-background">
        {badge && (
          <span
            className={`absolute left-3 top-3 z-10 rounded-full px-3 py-1 text-[10px] font-semibold uppercase tracking-widest shadow-sm ${
              badge.tone === "strong" ? "bg-brand text-white" : "bg-ink text-white"
            }`}
          >
            {badge.label}
          </span>
        )}
        <FavoriteButton
          slug={product.slug}
          className="absolute right-3 top-3 z-10 rounded-full bg-background/80 p-2 text-foreground/60 shadow-sm backdrop-blur-sm transition-colors hover:text-brand"
        />
        {product.image_url ? (
          <SafeProductImage
            src={product.image_url}
            alt={product.name}
            category={product.category}
            className="object-contain p-8 transition-transform duration-500 group-hover:scale-[1.04]"
          />
        ) : (
          <CategoryIcon category={product.category} />
        )}
      </div>

      <div className="flex flex-1 flex-col gap-4 p-6">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <span className="text-[11px] font-medium uppercase tracking-widest text-foreground/40">
              {CATEGORY_LABELS[product.category] ?? product.category} · {product.brand}
            </span>
            <h3 className="mt-1 line-clamp-2 font-display text-lg font-medium leading-snug text-foreground">
              {product.name}
            </h3>
          </div>
          <AiBuySignal
            buyScore={product.buy_score}
            buySignalScore={product.buy_signal_score}
            historySpanDays={product.history_span_days}
            size="sm"
          />
        </div>

        <div className="mt-auto flex items-end justify-between gap-3 border-t border-border pt-4">
          <div>
            {hasReliableTrend && pct !== null && pct < 0 && product.average_price !== null ? (
              <>
                <div className="text-xs text-foreground/35 line-through">
                  30日平均 {yen(product.average_price)}
                </div>
                <div className="font-display text-2xl font-semibold text-foreground">
                  {yen(product.current_price)}
                </div>
              </>
            ) : (
              <>
                <div className="font-display text-2xl font-semibold text-foreground">
                  {yen(product.current_price)}
                </div>
                {hasReliableTrend && product.average_price !== null ? (
                  <div className="mt-0.5 text-xs text-foreground/45">30日平均 {yen(product.average_price)}</div>
                ) : (
                  <div className="mt-0.5 text-xs text-foreground/35">
                    データ蓄積中（{product.history_span_days}日分）
                  </div>
                )}
              </>
            )}
          </div>
          {pct !== null && (
            <div className="text-right">
              <div
                className={`font-display text-lg font-semibold ${
                  pct < 0 ? "text-sale" : "text-foreground/60"
                }`}
              >
                {pct > 0 ? "+" : ""}
                {pct}%
              </div>
              <div className="text-[10px] uppercase tracking-widest text-foreground/35">
                {pct <= CAUTION_DISCOUNT_PERCENT ? "要確認" : pct < 0 ? "OFF" : "vs 30d avg"}
              </div>
            </div>
          )}
        </div>

        <CompareButton slug={product.slug} />
      </div>
    </Link>
  );
}
