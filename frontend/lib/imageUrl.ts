// Every product photo on this site is hotlinked from somewhere else - the
// Rakuten/Yahoo APIs (backend/app/rakuten.py, yahoo.py), a CSV import, or
// a URL typed into /admin/products - so nothing guarantees it's a usable
// https URL. This is the one place that decides what is safe to put in an
// <img src> (and the share-image renderer in lib/og.tsx).

/**
 * Returns a loadable https URL, or null when the value can't be one (the
 * caller then shows the NO IMAGE placeholder instead of a broken image).
 *
 * - null / "" / whitespace -> null
 * - "http://..." -> "https://..." (par-gear.com is served over https, so a
 *   plain-http image is mixed content: blocked or auto-upgraded by the
 *   browser anyway - upgrading it here makes that explicit and consistent;
 *   Rakuten's and Yahoo's image CDNs both serve https)
 * - "//host/..." (protocol-relative) -> "https://host/..."
 * - a same-site path ("/images/x.png") is kept as-is
 * - anything else (data:, javascript:, a bare relative path, an
 *   unparsable string) -> null
 */
export function normalizeImageUrl(raw: string | null | undefined): string | null {
  if (typeof raw !== "string") return null;
  const value = raw.trim();
  if (!value) return null;

  if (value.startsWith("/") && !value.startsWith("//")) return value;

  let candidate = value;
  if (candidate.startsWith("//")) {
    candidate = `https:${candidate}`;
  } else if (/^http:\/\//i.test(candidate)) {
    candidate = `https://${candidate.slice("http://".length)}`;
  }

  try {
    const url = new URL(candidate);
    if (url.protocol !== "https:" || !url.hostname) return null;
    return url.toString();
  } catch {
    return null;
  }
}
