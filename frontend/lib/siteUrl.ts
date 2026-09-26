// The site's own absolute origin, used for canonical URLs, sitemap/robots
// and - critically - og:image/twitter:image. Those must be absolute URLs a
// crawler can fetch: if NEXT_PUBLIC_SITE_URL were ever missing from a
// production build, falling back to localhost would silently ship
// "http://localhost:3000/..." share images and every X/LINE/Facebook card
// would render as a grey placeholder. NEXT_PUBLIC_* values are baked in at
// build time, so the production fallback is the real domain instead.
export const SITE_URL =
  process.env.NEXT_PUBLIC_SITE_URL ||
  (process.env.NODE_ENV === "production" ? "https://par-gear.com" : "http://localhost:3000");
