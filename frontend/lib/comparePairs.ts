// STEP69: "A vs B" comparison pages (/compare/[pair]).
//
// One URL per pair: the two slugs in alphabetical order joined by "-vs-",
// so A-vs-B and B-vs-A are the same page (the other order redirects).
// Rivals are picked from real data only - same category, closest current
// price, other makers first - never from claimed popularity.

export const PAIR_SEPARATOR = "-vs-";

export function pairSlug(a: string, b: string): string {
  return [a, b].sort().join(PAIR_SEPARATOR);
}

export function pairHref(a: string, b: string): string {
  return `/compare/${pairSlug(a, b)}`;
}

// Every way to split "x-vs-y" into two slugs (a slug could itself contain
// "-vs-"); the page tries them in order until both products exist.
export function pairCandidates(pair: string): [string, string][] {
  const out: [string, string][] = [];
  let from = 0;
  for (;;) {
    const i = pair.indexOf(PAIR_SEPARATOR, from);
    if (i < 0) break;
    const a = pair.slice(0, i);
    const b = pair.slice(i + PAIR_SEPARATOR.length);
    if (a && b && a !== b) out.push([a, b]);
    from = i + 1;
  }
  return out;
}

type RivalCandidate = { slug: string; brand: string; category: string; current_price: number | null };

export function nearestRivals<T extends RivalCandidate>(product: RivalCandidate, candidates: T[], limit = 3): T[] {
  const price = product.current_price;
  if (price === null || price <= 0) return [];
  return candidates
    .filter((c) => c.slug !== product.slug && c.category === product.category && c.current_price !== null && c.current_price > 0)
    .map((c) => ({
      c,
      otherMaker: c.brand.toLowerCase() !== product.brand.toLowerCase(),
      gap: Math.abs(Math.log((c.current_price as number) / price)),
    }))
    .sort((x, y) => Number(y.otherMaker) - Number(x.otherMaker) || x.gap - y.gap || x.c.slug.localeCompare(y.c.slug))
    .slice(0, limit)
    .map((x) => x.c);
}
