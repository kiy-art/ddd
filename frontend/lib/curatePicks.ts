import { Product } from "@/lib/api";

// Same "enough history to claim a trend" threshold used by ProductCard/
// AiBuySignal/product page - a pick built on thinner data than this would
// overstate what's actually known.
const THIN_DATA_DAYS = 7;

// Same tolerance rule-based reason text (analysis.py) and badges.ts use for
// "close enough to its own recorded low to call it a near-record price".
const NEAR_LOW_RATIO = 1.05;

export interface CuratedPick {
  label: string;
  product: Product;
}

function isReliable(p: Product): boolean {
  return p.buy_score !== "insufficient_data" && p.history_span_days >= THIN_DATA_DAYS;
}

/**
 * Builds the category page's "today's picks" strip - a handful of real,
 * checkable reasons to look at a product right now (spotlight / biggest
 * drop / near record low / buy signal / forecast), each backed by an
 * actual field already on the product (never a guess). Returns as many as
 * genuinely qualify (0-5), each product used at most once.
 */
export function curateTodaysPicks(products: Product[]): CuratedPick[] {
  const picks: CuratedPick[] = [];
  const used = new Set<number>();

  const take = (label: string, product: Product | undefined) => {
    if (!product || used.has(product.id)) return;
    picks.push({ label, product });
    used.add(product.id);
  };

  const spotlight = [...products]
    .filter(isReliable)
    .sort((a, b) => (b.buy_signal_score ?? -1) - (a.buy_signal_score ?? -1))[0];
  take("今日の注目", spotlight);

  const biggestDrop = [...products]
    .filter((p) => isReliable(p) && p.price_change_percent !== null && p.price_change_percent < 0)
    .sort((a, b) => (a.price_change_percent ?? 0) - (b.price_change_percent ?? 0))[0];
  take("大幅値下げ", biggestDrop);

  const nearLow = [...products]
    .filter(
      (p) =>
        isReliable(p) &&
        p.lowest_price !== null &&
        p.lowest_price > 0 &&
        p.current_price !== null &&
        p.current_price <= p.lowest_price * NEAR_LOW_RATIO
    )
    .sort((a, b) => a.current_price! / a.lowest_price! - b.current_price! / b.lowest_price!)[0];
  take("過去最安級", nearLow);

  const buyNow = [...products]
    .filter((p) => isReliable(p) && (p.buy_score === "strong_buy" || p.buy_score === "buy"))
    .sort((a, b) => (b.buy_signal_score ?? -1) - (a.buy_signal_score ?? -1))[0];
  take("買い時", buyNow);

  const forecastDown = [...products]
    .filter(
      (p) => p.forecast_trend === "down" && p.current_price !== null && p.forecast_center_price !== null
    )
    .sort((a, b) => b.current_price! - b.forecast_center_price! - (a.current_price! - a.forecast_center_price!))[0];
  take("値下がり予測", forecastDown);

  return picks;
}
