import { Product } from "@/lib/api";

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
