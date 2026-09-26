import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Explicit, not just relying on the (matching) default: every URL this
  // site generates - Link hrefs, sitemap.ts, canonical tags - is already
  // written without a trailing slash. Making that the enforced config
  // means a trailing-slash URL 308-redirects instead of serving content
  // directly, which matters for Search Console: a sitemap entry that
  // redirects is flagged as an error rather than indexed.
  trailingSlash: false,

  images: {
    // Every host the product-photo pipeline actually writes into
    // image_url: Rakuten Ichiba (backend/app/rakuten.py - mediumImageUrls,
    // served from thumbnail.image.rakuten.co.jp; the shop/cabinet hosts
    // below appear in some listings) and Yahoo!ショッピング
    // (backend/app/yahoo.py - image.medium, served from *.yimg.jp).
    // https only: lib/imageUrl.ts upgrades any http:// URL before it's used.
    //
    // Note: SafeProductImage renders with `unoptimized` (see the comment
    // there), which serves the CDN image as-is and doesn't consult this
    // list - it's the allowlist that applies if/when optimization is ever
    // turned on for these hosts, so it's kept in sync with the real sources
    // rather than left empty.
    remotePatterns: [
      { protocol: "https", hostname: "thumbnail.image.rakuten.co.jp" },
      { protocol: "https", hostname: "image.rakuten.co.jp" },
      { protocol: "https", hostname: "shop.r10s.jp" },
      { protocol: "https", hostname: "tshop.r10s.jp" },
      { protocol: "https", hostname: "item-shopping.c.yimg.jp" },
      { protocol: "https", hostname: "shopping.c.yimg.jp" },
      { protocol: "https", hostname: "**.yimg.jp" },
    ],
  },
};

export default nextConfig;
