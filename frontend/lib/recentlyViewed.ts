// Same per-browser-only localStorage approach as lib/favorites.ts.

const KEY = "par:recently-viewed";
const MAX_ITEMS = 8;

function safeGetSlugs(): string[] {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter((v): v is string => typeof v === "string") : [];
  } catch {
    return [];
  }
}

function safeSetSlugs(slugs: string[]): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(slugs));
  } catch {
    // storage unavailable - nothing to do
  }
}

export function getRecentlyViewed(): string[] {
  return safeGetSlugs();
}

export function trackViewed(slug: string): void {
  const current = safeGetSlugs().filter((s) => s !== slug);
  safeSetSlugs([slug, ...current].slice(0, MAX_ITEMS));
}
