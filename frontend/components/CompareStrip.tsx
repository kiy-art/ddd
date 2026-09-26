"use client";

import Link from "next/link";

import AiBuySignal from "@/components/AiBuySignal";
import { getAmazonSearchUrl } from "@/lib/amazon";
import { Product } from "@/lib/api";
import { trackAffiliateClick } from "@/lib/affiliateTracking";
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
      // A plain <div>, not a Link: the Amazon anchor below needs to sit
      // alongside the card's own navigation link, not nested inside it (an
      // <a> inside another <a> is invalid HTML, and this Next.js version's
      // Link intercepts the click before a nested element's own
      // preventDefault/stopPropagation can stop it - confirmed by testing,
      // not assumed).
      <div
        key={p.id}
        className={`flex flex-1 flex-col gap-2 rounded-2xl border p-5 transition-colors hover:border-brand/40 ${
          p.id === currentId ? "border-brand bg-card" : "border-border bg-background"
        }`}
      >
        <Link
          href={`/products/${p.slug}`}
          onClick={() =>
            trackEvent("compare_click", {
              product_id: p.id,
              product_slug: p.slug,
              is_current_product: p.id === currentId,
            })
          }
          className="flex flex-col gap-2"
        >
          <span className="text-[11px] font-medium uppercase tracking-widest text-foreground/40">{p.brand}</span>
          <span className="line-clamp-2 font-display text-sm font-medium text-foreground">{p.name}</span>
          <span className="font-num text-lg font-semibold text-foreground">{yen(p.current_price)}</span>
          {p.forecast_confidence !== null && p.forecast_low_price !== null && p.forecast_high_price !== null && (
            <span className="text-[11px] text-accent-dark">
              予測 {yen(p.forecast_low_price)}〜{yen(p.forecast_high_price)}
            </span>
          )}
          <div className="mt-1">
            <AiBuySignal
              buyScore={p.buy_score}
              buySignalScore={p.buy_signal_score}
              historySpanDays={p.history_span_days}
              msrp={p.msrp}
              currentPrice={p.current_price}
              releaseDate={p.release_date}
              size="sm"
            />
          </div>
        </Link>
        <a
          href={getAmazonSearchUrl(p.name)}
          target="_blank"
          rel="noopener noreferrer sponsored"
          onClick={() => {
            trackEvent("cta_click", {
              product_id: p.id,
              product_slug: p.slug,
              product_name: p.name,
              cta_type: "affiliate_search",
              list_source: "compare_strip",
            });
            trackAffiliateClick({ productId: p.id, category: p.category, shop: "amazon", placement: "compare_strip" });
          }}
          className="mt-1 inline-flex w-fit items-center gap-1 rounded-full border border-border px-2 py-1 text-[10px] font-semibold text-foreground/60 transition-colors hover:border-brand/40 hover:text-brand"
        >
          Amazonで探す ↗
        </a>
        {p.id === currentId && (
          <span className="mt-1 w-fit rounded-full bg-brand px-2 py-0.5 text-[10px] font-semibold text-on-brand">
            この商品
          </span>
        )}
      </div>
    );
  });

  const compareUrl = `/compare?slugs=${products.map((p) => encodeURIComponent(p.slug)).join(",")}`;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-stretch">{nodes}</div>
      <Link
        href={compareUrl}
        onClick={() => trackEvent("compare_table_click", { product_ids: products.map((p) => p.id).join(",") })}
        className="self-start text-sm font-semibold text-brand hover:underline"
      >
        詳しく比較する（表で見る） →
      </Link>
    </div>
  );
}
