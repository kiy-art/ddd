// Per-browser only (localStorage), same constraints as favorites.ts: no
// account system, so this never syncs across devices or reaches the
// backend, and every access is wrapped in try/catch since localStorage can
// throw (private browsing, blocked storage).

const KEY = "par:compare";
export const MAX_COMPARE = 4;

// useSyncExternalStore requires getSnapshot to return a referentially
// stable value when the underlying data hasn't changed - re-parsing
// localStorage into a new array on every call (as favorites.ts's
// getFavorites does) is fine there because every consumer only reads a
// derived primitive (a boolean/number) from it, but CompareBar reads the
// array itself as its snapshot, and a fresh array reference every render
// sent React into "Maximum update depth exceeded". This tiny cache keeps
// the same array reference across calls until the raw stored value
// actually changes.
let cachedRaw: string | null = null;
let cachedList: string[] = [];

function safeGetSlugs(): string[] {
  let raw: string | null;
  try {
    raw = localStorage.getItem(KEY);
  } catch {
    return cachedList;
  }
  if (raw === cachedRaw) return cachedList;
  cachedRaw = raw;
  try {
    if (!raw) {
      cachedList = [];
    } else {
      const parsed = JSON.parse(raw);
      cachedList = Array.isArray(parsed) ? parsed.filter((v): v is string => typeof v === "string") : [];
    }
  } catch {
    cachedList = [];
  }
  return cachedList;
}

function safeSetSlugs(slugs: string[]): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(slugs));
  } catch {
    // storage unavailable - the toggle just won't persist, not worth surfacing an error for
  }
  cachedRaw = JSON.stringify(slugs);
  cachedList = slugs;
}

export function getCompareList(): string[] {
  return safeGetSlugs();
}

export function isInCompare(slug: string): boolean {
  return safeGetSlugs().includes(slug);
}

// Same pub-sub + useSyncExternalStore pairing as favorites.ts, so every
// CompareButton and the floating CompareBar stay in sync without an effect.
type Listener = () => void;
const listeners = new Set<Listener>();

export function subscribe(listener: Listener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** Toggles a product slug in the compare list. No-ops past MAX_COMPARE. */
export function toggleCompare(slug: string): void {
  const current = safeGetSlugs();
  let next: string[];
  if (current.includes(slug)) {
    next = current.filter((s) => s !== slug);
  } else {
    if (current.length >= MAX_COMPARE) return;
    next = [...current, slug];
  }
  safeSetSlugs(next);
  listeners.forEach((l) => l());
}

export function removeFromCompare(slug: string): void {
  const current = safeGetSlugs();
  safeSetSlugs(current.filter((s) => s !== slug));
  listeners.forEach((l) => l());
}

export function clearCompare(): void {
  safeSetSlugs([]);
  listeners.forEach((l) => l());
}
