import type { PriceHistoryItem, Product } from "@/lib/api";

export interface Deal {
  product: Product;
  dropPercent: number;
}

/** Products whose price actually fell since the last recorded price point,
 * sorted by the size of that drop. Never fabricated - both prices are real
 * recorded values. */
export function computeDeals(products: Product[]): Deal[] {
  const deals: Deal[] = [];
  for (const product of products) {
    if (product.current_price === null || product.previous_price === null) continue;
    if (product.current_price >= product.previous_price) continue;
    const dropPercent = Math.round((1 - product.current_price / product.previous_price) * 1000) / 10;
    deals.push({ product, dropPercent });
  }
  return deals.sort((a, b) => b.dropPercent - a.dropPercent);
}

/** A drop at or above this percent is shown without the percent: such a gap
 * is more likely a different seller/set/coupon price than a real markdown
 * (SE audit 2026-10-25). Prices stay visible so nothing is hidden. */
export const DROP_VERIFY_PERCENT = 25;

const yen = (n: number | null) => (n === null ? "" : `¥${n.toLocaleString("ja-JP")}`);

/** Heading text for a deal: states the basis ("前回記録") and both prices. */
export function dropLabel({ product, dropPercent }: Deal): string {
  const span = `前回記録 ${yen(product.previous_price)} → ${yen(product.current_price)}`;
  return dropPercent >= DROP_VERIFY_PERCENT
    ? `${span}（記録上の差。販売店・条件の違いの可能性あり）`
    : `${span}（${dropPercent}% 値下がり）`;
}

// --- Guide-only selection (PAR. P-015, 2026-11-27; audit fix same night) ----
// The sale guide's "値下がり" slot should show products whose price was steady
// and then fell, not listing swaps or one-day bounces. The list endpoint has no
// history, and the 30-day average can be pulled up by a swapped listing, so the
// final check reads each candidate's real price history (audit 2026-11-27:
// e.g. a price that was 13,860 for 15 days, 16,500 for one day, then 13,860
// again must not be shown as a 16% drop).

/** Candidate drop range (percent vs the previous record). >= DROP_VERIFY_PERCENT
 * is more likely a different seller/set/coupon. */
export const STABLE_MIN_DROP_PERCENT = 3;
/** The previous price must have held for this many consecutive records. */
export const STABLE_MIN_HOLD_RECORDS = 3;
/** The current price must not have appeared within this many days before
 * (excludes prices that flip between two listings). */
export const STABLE_LOOKBACK_DAYS = 30;
/** Max items per category, so one category (ball) cannot fill the slot. */
export const STABLE_MAX_PER_CATEGORY = 2;
/** How many candidates get a history check (one detail request each). */
export const STABLE_MAX_CANDIDATES = 12;

/** Candidates for the guide slot (no history yet): a 3-25% drop vs the previous
 * record, largest first, one per product name so the same model listed twice
 * does not take two places. */
export function stableDealCandidates(products: Product[]): Deal[] {
  const seen = new Set<string>();
  return computeDeals(products)
    .filter((d) => d.dropPercent >= STABLE_MIN_DROP_PERCENT && d.dropPercent < DROP_VERIFY_PERCENT)
    .filter((d) => {
      const key = d.product.name.trim();
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    })
    .slice(0, STABLE_MAX_CANDIDATES);
}

/** True when the latest record is a drop from a price that held for
 * STABLE_MIN_HOLD_RECORDS records in a row, and the new price was not seen in
 * the STABLE_LOOKBACK_DAYS before that run. */
export function heldThenDropped(history: PriceHistoryItem[]): boolean {
  const h = [...history].sort((a, b) => a.recorded_at.localeCompare(b.recorded_at));
  if (h.length < STABLE_MIN_HOLD_RECORDS + 1) return false;
  const current = h[h.length - 1];
  const prev = h[h.length - 2].price;
  if (current.price >= prev) return false;
  let run = 0;
  for (let i = h.length - 2; i >= 0 && h[i].price === prev; i--) run++;
  if (run < STABLE_MIN_HOLD_RECORDS) return false;
  const since = new Date(current.recorded_at).getTime() - STABLE_LOOKBACK_DAYS * 86400000;
  return !h
    .slice(0, h.length - 1)
    .some((x) => x.price <= current.price && new Date(x.recorded_at).getTime() >= since);
}

/** Spread verified deals over categories (at most STABLE_MAX_PER_CATEGORY
 * each, largest drop first). Never padded: fewer than `limit`, or none, is
 * allowed. */
export function spreadByCategory(deals: Deal[], limit: number): Deal[] {
  const groups = new Map<string, Deal[]>();
  for (const d of deals) {
    const list = groups.get(d.product.category);
    if (list) list.push(d);
    else groups.set(d.product.category, [d]);
  }
  const out: Deal[] = [];
  for (let round = 0; round < STABLE_MAX_PER_CATEGORY && out.length < limit; round++) {
    for (const list of groups.values()) {
      if (list[round] && out.length < limit) out.push(list[round]);
    }
  }
  return out;
}
