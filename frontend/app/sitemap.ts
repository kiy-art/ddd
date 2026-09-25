import type { MetadataRoute } from "next";

import { CATEGORIES, getBrands, getProducts } from "@/lib/api";
import { GUIDES } from "@/lib/guides";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";

// Regenerated at most once per hour (ISR) instead of on every crawl
// request. Render's free-tier backend sleeps after ~15 minutes idle and
// can take tens of seconds to wake up; without this, every single
// Googlebot hit would depend on a live, possibly-cold-starting backend
// call, which is exactly the kind of slow/timed-out response that led to
// Search Console reporting 0 discovered pages. If regeneration fails (see
// the timeout and the deliberately-uncaught fetch below), Next.js keeps
// serving the last successfully generated sitemap instead of a broken or
// incomplete one, and retries again on the next request after this window
// (see node_modules/next/dist/docs/01-app/02-guides/
// incremental-static-regeneration.md).
export const revalidate = 3600;

// The backend call itself has no built-in timeout, so a slow/cold-starting
// instance could otherwise hang the whole route far longer than any
// crawler will wait. Racing it against a short timeout makes a bad
// generation attempt fail fast, which - combined with `revalidate` above -
// means visitors and crawlers alike keep getting the last good sitemap
// almost immediately instead of waiting on a stalled request.
const FETCH_TIMEOUT_MS = 8000;

function withTimeout<T>(promise: Promise<T>, ms: number): Promise<T> {
  return Promise.race([
    promise,
    new Promise<T>((_, reject) => {
      setTimeout(() => reject(new Error(`sitemap: fetch timed out after ${ms}ms`)), ms);
    }),
  ]);
}

function sitemapUrl(path: string): string {
  return `${SITE_URL}${path}`;
}

// Google Search Console flagged 50 <lastmod> entries as invalid dates
// ("無効な日付：日付の値が無効です"). Root cause: the backend serializes
// Product.updated_at as a naive UTC datetime string with no timezone
// designator (e.g. "2026-09-25T00:48:09", not "...Z" - see
// app/models.py's `server_default=func.now()`, always UTC on this stack,
// but the string itself never says so). A date-TIME string that omits a
// timezone isn't valid W3C Datetime/RFC 3339 on its own (only a bare
// DATE, no time-of-day, is allowed to omit it) - and Next.js only
// produces a spec-correct <lastmod> when `lastModified` is an actual
// Date object (it calls .toISOString() on it); a raw string is written
// into the XML completely unvalidated (see
// node_modules/next/dist/build/webpack/loaders/metadata/resolve-route-data.js).
// This turns every date value into a real Date first - explicitly
// treating a timezone-less date-TIME as UTC (matching how it was
// actually generated) rather than leaning on the JS engine's local-time
// interpretation of a bare "YYYY-MM-DDTHH:mm:ss" string, which would
// only coincidentally be correct on a UTC-configured server - and drops
// anything that still fails to parse instead of ever emitting another
// invalid <lastmod>.
function toLastModified(value: string | null | undefined): Date | undefined {
  if (!value) return undefined;
  const hasTimeComponent = value.includes("T");
  const hasTimezone = /Z$|[+-]\d{2}:\d{2}$/.test(value);
  const normalized = hasTimeComponent && !hasTimezone ? `${value}Z` : value;
  const date = new Date(normalized);
  return Number.isNaN(date.getTime()) ? undefined : date;
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const staticEntries: MetadataRoute.Sitemap = [
    { url: sitemapUrl(""), changeFrequency: "daily", priority: 1 },
    { url: sitemapUrl("/deals"), changeFrequency: "daily", priority: 0.8 },
    { url: sitemapUrl("/ranking"), changeFrequency: "daily", priority: 0.8 },
    { url: sitemapUrl("/brands"), changeFrequency: "weekly", priority: 0.5 },
    { url: sitemapUrl("/guides"), changeFrequency: "weekly", priority: 0.5 },
    { url: sitemapUrl("/faq"), changeFrequency: "monthly", priority: 0.4 },
    { url: sitemapUrl("/disclaimer"), changeFrequency: "yearly", priority: 0.2 },
    ...CATEGORIES.map((category) => ({
      url: sitemapUrl(`/category/${category}`),
      changeFrequency: "daily" as const,
      priority: 0.7,
    })),
    ...GUIDES.map((guide) => ({
      url: sitemapUrl(`/guides/${guide.slug}`),
      lastModified: toLastModified(guide.publishedAt),
      changeFrequency: "monthly" as const,
      priority: 0.5,
    })),
  ];

  // Deliberately not wrapped in try/catch: a transient backend failure
  // (including the timeout above) must propagate so Next.js's ISR keeps
  // serving the last known-good sitemap (see the `revalidate` comment)
  // instead of silently publishing one that's missing every product and
  // brand URL - which is what the previous try/catch-to-empty-array
  // version did on every fetch failure.
  const [products, brands] = await Promise.all([
    withTimeout(getProducts(), FETCH_TIMEOUT_MS),
    withTimeout(getBrands(), FETCH_TIMEOUT_MS),
  ]);

  const productEntries: MetadataRoute.Sitemap = products
    .filter((product) => Boolean(product.slug))
    .map((product) => ({
      url: sitemapUrl(`/products/${product.slug}`),
      lastModified: toLastModified(product.updated_at),
      changeFrequency: "daily",
      priority: 0.8,
    }));

  const brandEntries: MetadataRoute.Sitemap = brands
    .filter((b) => Boolean(b.brand))
    .map((b) => ({
      url: sitemapUrl(`/brand/${encodeURIComponent(b.brand)}`),
      changeFrequency: "daily",
      priority: 0.6,
    }));

  // De-duplicated by URL as a final safety net - Search Console flags
  // duplicate <loc> entries, and this guarantees one can never slip
  // through even if two data sources happened to produce the same URL.
  const seen = new Set<string>();
  return [...staticEntries, ...productEntries, ...brandEntries].filter((entry) => {
    if (seen.has(entry.url)) return false;
    seen.add(entry.url);
    return true;
  });
}
