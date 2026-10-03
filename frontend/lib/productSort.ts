import type { Product } from "@/lib/api";

// Shared by the category page and the STEP69 brand x category pages.
export const SORT_OPTIONS = ["discount", "signal", "price_asc"] as const;
export type SortOption = (typeof SORT_OPTIONS)[number];

export const SORT_LABELS: Record<SortOption, string> = {
  discount: "値下がり幅順",
  signal: "買い時順",
  price_asc: "価格が安い順",
};

export function isSortOption(value: string | undefined): value is SortOption {
  return !!value && (SORT_OPTIONS as readonly string[]).includes(value);
}

export function sortProducts(products: Product[], sort: SortOption): Product[] {
  const list = [...products];
  if (sort === "signal") {
    return list.sort((a, b) => (b.buy_signal_score ?? -1) - (a.buy_signal_score ?? -1));
  }
  if (sort === "price_asc") {
    return list.sort((a, b) => (a.current_price ?? Infinity) - (b.current_price ?? Infinity));
  }
  // "discount": already the API's default order (price_change_percent ascending), kept as-is
  return list;
}
