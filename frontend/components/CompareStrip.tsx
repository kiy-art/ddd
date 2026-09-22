"use client";

import Link from "next/link";

import AiBuySignal from "@/components/AiBuySignal";
import { Product } from "@/lib/api";
import { trackEvent } from "@/lib/analytics";

function yen(value: number | null): string {
  if (value === null) return "-";
  return `¥${value.toLocaleString("ja-JP")}`;
}

export default function CompareStrip({ products, currentId }: { products: Product[]; currentId?: number }) {
  if (products.length < 2) return null;

  const nodes: React.ReactNode[] = [];
  products.forEach((p, i) => {
    if (i > 0) {
      nodes.push(
        <div key={`vs-${p.id}`} className="hidden shrink-0 items-center px-1 text-[11px] font-semibold text-foreground/30 sm:flex">
          VS
        </div>
      );
    }
    nodes.push(
      <Link
        key={p.id}
        href={`/products/${p.slug}`}
        onClick={() =>
          trackEvent("compare_click", {
            product_id: p.id,
            product_slug: p.slug,
            is_current_product: p.id === currentId,
          })
        }
        className={`flex flex-1 flex-col gap-2 rounded-2xl border p-5 transition-colors hover:border-brand/40 ${
          p.id === currentId ? "border-brand bg-card" : "border-border bg-background"
        }`}
      >
        <span className="text-[11px] font-medium uppercase tracking-widest text-foreground/40">{p.brand}</span>
        <span className="line-clamp-2 font-display text-sm font-medium text-foreground">{p.name}</span>
        <span className="font-display text-lg font-semibold text-foreground">{yen(p.current_price)}</span>
        {p.forecast_confidence !== null && p.forecast_low_price !== null && p.forecast_high_price !== null && (
          <span className="text-[11px] text-accent-dark">
            🔮 予測 {yen(p.forecast_low_price)}〜{yen(p.forecast_high_price)}
          </span>
        )}
        <div className="mt-1">
          <AiBuySignal
            buyScore={p.buy_score}
            buySignalScore={p.buy_signal_score}
            historySpanDays={p.history_span_days}
            size="sm"
          />
        </div>
        {p.id === currentId && (
          <span className="mt-1 w-fit rounded-full bg-brand px-2 py-0.5 text-[10px] font-semibold text-white">
            この商品
          </span>
        )}
      </Link>
    );
  });

  return <div className="flex flex-col gap-3 sm:flex-row sm:items-stretch">{nodes}</div>;
}
