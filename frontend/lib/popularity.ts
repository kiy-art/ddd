import type { Product } from "@/lib/api";

// A Rakuten bestseller rank older than this is no longer "now" - it's not
// shown as a live fact anywhere (badge, /popular, homepage). Same window
// the X post uses (backend app/x_post.py POPULARITY_MAX_AGE_DAYS).
export const POPULARITY_MAX_AGE_DAYS = 3;

// Backend timestamps are naive UTC ("2026-09-25T00:48:09") - parse as UTC.
export function parseUtc(value: string): number {
  const hasZone = /Z$|[+-]\d{2}:?\d{2}$/.test(value);
  return new Date(value.includes("T") && !hasZone ? `${value}Z` : value).getTime();
}

/**
 * The product's Rakuten rank if it was confirmed recently, else null.
 * STEP51: when the daily ranking sync failed (it did, every day, until its
 * missing accessKey was fixed) the last stored rank stayed in the DB - and
 * was shown as current indefinitely. A rank is only a claim about "right
 * now" if it was actually re-confirmed within the last few days.
 */
export function freshPopularityRank(
  p: Pick<Product, "popularity_rank" | "popularity_updated_at">,
  now: number = Date.now()
): number | null {
  if (p.popularity_rank === null || !p.popularity_updated_at) return null;
  const age = now - parseUtc(p.popularity_updated_at);
  return age <= POPULARITY_MAX_AGE_DAYS * 24 * 60 * 60 * 1000 ? p.popularity_rank : null;
}

/** Most recent successful ranking confirmation across products, or null. */
export function latestPopularityUpdate(products: Pick<Product, "popularity_updated_at">[]): Date | null {
  const times = products.map((p) => (p.popularity_updated_at ? parseUtc(p.popularity_updated_at) : NaN)).filter((t) => !Number.isNaN(t));
  return times.length > 0 ? new Date(Math.max(...times)) : null;
}
