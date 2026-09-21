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
