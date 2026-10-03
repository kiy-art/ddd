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

// STEP69: the brand x category page URL (/category/driver/ping). Brands
// are stored as canonical English names (backend app/brands.py), so a
// lowercase ASCII slug is stable; anything else falls back to encoding.
export function brandSlug(brand: string): string {
  const slug = brand
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return slug || encodeURIComponent(brand.trim());
}

export function brandCategoryHref(category: string, brand: string, sort?: string | null): string {
  const base = `/category/${category}/${brandSlug(brand)}`;
  return sort && sort !== "discount" ? `${base}?sort=${sort}` : base;
}

// Fewer than this and the page is too thin to be worth a search result
// of its own (still reachable, but noindex and left out of the sitemap).
export const BRAND_PAGE_MIN_PRODUCTS = 2;
