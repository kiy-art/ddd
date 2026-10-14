import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/siteUrl";

// Crawlers that bring PAR. no visitors but walk every product, category,
// brand and comparison page - each page view costs Render outbound
// bandwidth (Hobby plan: 5GB/month, then billed). SEO-tool and data-
// harvesting bots only; search engines (Googlebot, Bingbot) and AI answer
// engines that can cite PAR. stay allowed.
const BLOCKED_BOTS = [
  "AhrefsBot",
  "SemrushBot",
  "MJ12bot",
  "DotBot",
  "BLEXBot",
  "DataForSeoBot",
  "SeznamBot",
  "PetalBot",
  "Bytespider",
  "Amazonbot",
  "CCBot",
  "magpie-crawler",
  "serpstatbot",
  "barkrowler",
];

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        // Re-sorted / re-tabbed copies of list pages, ad-hoc comparisons and
        // the noindex search/finder results add nothing to index but
        // multiply the URLs a crawler fetches. The base list pages and the
        // fixed /compare/<a>-vs-<b> pages stay crawlable.
        disallow: ["/admin", "/alerts", "/*?*sort=", "/*?*tab=", "/search", "/finder", "/compare?"],
        // Honoured by Bing and most other crawlers (Google ignores it).
        crawlDelay: 5,
      },
      {
        userAgent: BLOCKED_BOTS,
        disallow: "/",
      },
    ],
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
