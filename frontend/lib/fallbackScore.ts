function clamp(value: number, lo: number, hi: number): number {
  return Math.max(lo, Math.min(hi, value));
}

// Same weighting split the business strategy decided on for the interim
// (pre-price-history) period: MSRP discount is the primary signal, days
// since release is a secondary, softer one.
const MSRP_WEIGHT = 0.7;
const RELEASE_WEIGHT = 0.3;

// Below this many days since release, a product's price is still very
// likely anchored near MSRP (same reasoning as forecast.py's
// RECENT_RELEASE_DAYS cap) - recency alone shouldn't earn any score boost
// yet, since there's no real evidence of a cycle-driven discount.
const RELEASE_RAMP_START_DAYS = 90;
// Beyond this many days, "older models tend to see more discounting" is a
// real, general pattern - but only a generic prior, not evidence about
// this specific unit's price, so it's capped at a modest max contribution.
const RELEASE_RAMP_END_DAYS = 365;
const MAX_RELEASE_COMPONENT = 0.4;

export interface FallbackScore {
  score: number; // 1-99, same range as the server-computed buy_signal_score
  // Same sign convention already used across the site (ProductCard.tsx,
  // product page): negative = cheaper than MSRP, positive = above it.
  msrpPct: number;
}

/**
 * A presentation-only substitute for buy_signal_score, computed entirely
 * client-side from fields the API already sends (msrp/current_price/
 * release_date) - for the many products that clear the backend's own
 * "insufficient_data" publish gate (crud.list_products) but haven't yet
 * built up the 7 days of history AiBuySignal wants before showing a real,
 * price-history-driven score. Never persisted, never used for buy_score/
 * sorting/filtering - purely so the gauge shows a real (if lower-
 * confidence) number instead of "ANALYZING" next to a product that's
 * already publicly listed.
 *
 * Returns null whenever msrp is missing - there is nothing to compare
 * against, and this deliberately does not fall back to guessing.
 */
export function getFallbackValueScore(product: {
  msrp: number | null;
  current_price: number | null;
  release_date: string | null;
}): FallbackScore | null {
  if (product.msrp === null || product.msrp <= 0 || product.current_price === null) return null;

  const msrpPct = ((product.current_price - product.msrp) / product.msrp) * 100;
  const msrpComponent = clamp(-msrpPct / 30, -1, 1); // -30% (cheap) -> +1, +30% (pricey) -> -1

  let releaseComponent = 0;
  if (product.release_date) {
    const daysSinceRelease = (Date.now() - new Date(product.release_date).getTime()) / 86400000;
    if (daysSinceRelease >= RELEASE_RAMP_END_DAYS) {
      releaseComponent = MAX_RELEASE_COMPONENT;
    } else if (daysSinceRelease >= RELEASE_RAMP_START_DAYS) {
      const progress = (daysSinceRelease - RELEASE_RAMP_START_DAYS) / (RELEASE_RAMP_END_DAYS - RELEASE_RAMP_START_DAYS);
      releaseComponent = MAX_RELEASE_COMPONENT * progress;
    }
  }

  const combined = msrpComponent * MSRP_WEIGHT + releaseComponent * RELEASE_WEIGHT;
  const score = Math.round(clamp(50 + combined * 49, 1, 99));

  return { score, msrpPct: Math.round(msrpPct * 10) / 10 };
}
