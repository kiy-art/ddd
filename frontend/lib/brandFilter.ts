import type { Product } from "@/lib/api";

// STEP64: the maker filter on category pages. Built only from the brands
// the category's products actually have - no fixed brand list to drift.

export type BrandCount = { brand: string; count: number };

export function brandCounts(products: Pick<Product, "brand">[]): BrandCount[] {
  const counts = new Map<string, number>();
  for (const p of products) {
    const brand = p.brand?.trim();
    if (brand) counts.set(brand, (counts.get(brand) ?? 0) + 1);
  }
  return [...counts.entries()]
    .map(([brand, count]) => ({ brand, count }))
    .sort((a, b) => b.count - a.count || a.brand.localeCompare(b.brand, "ja"));
}

// A ?brand= value that isn't one of this category's brands is ignored
// (shows every product) rather than rendering an empty page.
export function selectedBrand(value: string | undefined, brands: BrandCount[]): string | null {
  if (!value) return null;
  return brands.some((b) => b.brand === value) ? value : null;
}

// Category page URL keeping the other filter: sort and brand combine.
export function categoryHref(category: string, params: { sort?: string | null; brand?: string | null }): string {
  const qs = new URLSearchParams();
  if (params.sort && params.sort !== "discount") qs.set("sort", params.sort);
  if (params.brand) qs.set("brand", params.brand);
  const query = qs.toString();
  return `/category/${category}${query ? `?${query}` : ""}`;
}
