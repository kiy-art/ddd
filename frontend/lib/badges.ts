import { Product } from "@/lib/api";

// Same threshold used by ProductCard/AiBuySignal/product page: below this
// many days of history, any confident claim (including a badge) would
// overstate what the data actually supports.
const THIN_DATA_DAYS = 7;

// "Near its own recorded low" - a plain, checkable fact rather than a
// subjective claim, using the same 5% tolerance as the rule-based reason
// text in analysis.py.
const NEAR_LOW_RATIO = 1.05;

export type BadgeTone = "strong" | "value";

export interface ProductBadge {
  label: string;
  tone: BadgeTone;
}

/**
 * Deliberately keyed off buy_score (the same category the gauge label and
 * product-page verdict already use), not the raw buy_signal_score number -
 * the two can diverge (buy_signal_score also weighs momentum/rank/distance
 * from the low), and a badge that says "STRONG BUY" next to a gauge that
 * says "HOLD" would contradict itself. No per-product attribute we can't
 * verify is ever used here (no "premium pick", "best for beginners", etc).
 */
export function getProductBadge(product: Product): ProductBadge | null {
  const reliable = product.buy_score !== "insufficient_data" && product.history_span_days >= THIN_DATA_DAYS;
  if (!reliable) return null;

  const nearAllTimeLow =
    product.lowest_price !== null &&
    product.current_price !== null &&
    product.current_price <= product.lowest_price * NEAR_LOW_RATIO;

  if (product.buy_score === "strong_buy") {
    return nearAllTimeLow ? { label: "過去最安値圏", tone: "strong" } : { label: "STRONG BUY", tone: "strong" };
  }
  if (product.buy_score === "buy") {
    return { label: "コスパ良し", tone: "value" };
  }
  return null;
}
