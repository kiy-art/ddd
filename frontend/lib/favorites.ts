// Per-browser only (localStorage) - no account system exists, so this
// never syncs across devices and is never sent to the backend. Every
// access is wrapped in try/catch: localStorage can throw (private
// browsing, blocked storage) and the page must still work without it.

const KEY = "par:favorites";

function safeGetSlugs(key: string): string[] {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter((v): v is string => typeof v === "string") : [];
  } catch {
    return [];
  }
}

function safeSetSlugs(key: string, slugs: string[]): void {
  try {
    localStorage.setItem(key, JSON.stringify(slugs));
  } catch {
    // storage unavailable - the toggle just won't persist, not worth surfacing an error for
  }
}

export function getFavorites(): string[] {
  return safeGetSlugs(KEY);
}

export function isFavorite(slug: string): boolean {
  return safeGetSlugs(KEY).includes(slug);
}

// Plain pub-sub so every FavoriteButton for the same product (a card in a
// grid and, say, the product detail page open in another tab of the same
// flow) re-renders when any of them toggles it - paired with
// useSyncExternalStore in components/FavoriteButton.tsx instead of
// effect+setState, since localStorage has no built-in same-tab change event.
type Listener = () => void;
const listeners = new Set<Listener>();

export function subscribe(listener: Listener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** Toggles favorite state for a product slug. */
export function toggleFavorite(slug: string): void {
  const current = safeGetSlugs(KEY);
  const next = current.includes(slug) ? current.filter((s) => s !== slug) : [...current, slug];
  safeSetSlugs(KEY, next);
  listeners.forEach((l) => l());
}
