import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Explicit, not just relying on the (matching) default: every URL this
  // site generates - Link hrefs, sitemap.ts, canonical tags - is already
  // written without a trailing slash. Making that the enforced config
  // means a trailing-slash URL 308-redirects instead of serving content
  // directly, which matters for Search Console: a sitemap entry that
  // redirects is flagged as an error rather than indexed.
  trailingSlash: false,
};

export default nextConfig;
