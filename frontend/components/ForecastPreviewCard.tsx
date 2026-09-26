"use client";

import Link from "next/link";

import { Product } from "@/lib/api";
import { forecastMonthLabel } from "@/lib/forecast";
import { trackEvent } from "@/lib/analytics";

function yen(value: number | null): string {
  if (value === null) return "-";
  return `¥${value.toLocaleString("ja-JP")}`;
}

export default function ForecastPreviewCard({ product }: { product: Product }) {
  return (
    <Link
      href={`/products/${product.slug}`}
      onClick={() =>
        trackEvent("forecast_preview_click", { product_id: product.id, product_slug: product.slug })
      }
      className="flex flex-col gap-4 rounded-2xl border border-border bg-card p-6 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-[0_24px_48px_-24px_rgba(20,19,15,0.22)]"
    >
      <span className="text-[11px] font-medium uppercase tracking-widest text-foreground/40">
        {product.brand}
      </span>
      <h3 className="line-clamp-2 font-display text-lg font-medium leading-snug text-foreground">
        {product.name}
      </h3>

      <div className="flex items-end justify-between gap-3 border-t border-border pt-4">
        <div>
          <span className="text-xs text-foreground/45">現在</span>
          <p className="font-num text-xl font-semibold text-foreground">{yen(product.current_price)}</p>
        </div>
        <div className="text-right">
          <span className="text-xs text-accent-dark">予測</span>
          <p className="font-num text-lg font-semibold text-accent-dark">
            {yen(product.forecast_low_price)}〜{yen(product.forecast_high_price)}
          </p>
        </div>
      </div>

      <div className="flex items-center justify-between rounded-lg bg-background px-3 py-2 text-xs text-foreground/50">
        <span>予測時期 {forecastMonthLabel(product.forecast_target_date!)}</span>
        <span className="font-semibold text-brand">分析を見る →</span>
      </div>
    </Link>
  );
}
