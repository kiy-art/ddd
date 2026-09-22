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

// Below this rank, a Rakuten category ranking position is too far down to
// read as a meaningful "popular" signal to a visitor at a glance.
const POPULARITY_BADGE_MAX_RANK = 10;

/**
 * A real third-party signal (Rakuten Ichiba's own bestseller ranking for
 * this product's category - see app/popularity.py), not this site's own
 * still-low traffic and not a guess. Kept as a separate badge from
 * getProductBadge above since it answers a different question ("is this
 * actually selling well elsewhere") from the buy-timing ones.
 */
export function getPopularityBadge(product: Product): ProductBadge | null {
  if (product.popularity_rank === null || product.popularity_rank > POPULARITY_BADGE_MAX_RANK) return null;
  return { label: `🔥 楽天人気${product.popularity_rank}位`, tone: "strong" };
}

// Manufacturer-stated lineup positioning (see the comment on
// Product.skill_level in the backend) - researched facts, not a guess from
// price/specs, so this stays a plain neutral label rather than a colored
// "buy me" style badge like getProductBadge/getPopularityBadge above.
export const SKILL_LEVEL_LABELS: Record<string, string> = {
  beginner: "初心者向け",
  all_levels: "オールレベル向け",
  advanced: "上級者向け",
};

export const PERFORMANCE_TYPE_LABELS: Record<string, string> = {
  distance: "飛距離重視",
  forgiveness: "やさしさ重視",
  control: "操作性重視",
  balanced: "バランス型",
};

export interface PositioningFact {
  label: string;
}

/**
 * Only the dimensions that were actually researched for this product - never
 * fills in a guess for a None field, per the site's anti-fabrication rule.
 * Returns [] (render nothing) when none of the three facts are known yet.
 */
export function getPositioningFacts(product: Product): PositioningFact[] {
  const facts: PositioningFact[] = [];
  if (product.skill_level && SKILL_LEVEL_LABELS[product.skill_level]) {
    facts.push({ label: SKILL_LEVEL_LABELS[product.skill_level] });
  }
  if (product.performance_type && PERFORMANCE_TYPE_LABELS[product.performance_type]) {
    facts.push({ label: PERFORMANCE_TYPE_LABELS[product.performance_type] });
  }
  if (product.is_current_generation !== null) {
    facts.push({ label: product.is_current_generation ? "現行モデル" : "型落ちモデル" });
  }
  return facts;
}
