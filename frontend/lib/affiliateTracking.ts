import { API_URL } from "@/lib/api";
import { trackEvent } from "@/lib/analytics";

// Kept in sync with backend/app/models.py's AFFILIATE_SHOPS.
export type Shop = "amazon" | "rakuten" | "yahoo" | "official";

export function detectShop(url: string): Shop {
  try {
    const host = new URL(url).hostname;
    if (host.includes("rakuten.co.jp")) return "rakuten";
    if (host.includes("amazon.co.jp") || host.includes("amazon.com")) return "amazon";
    if (host.includes("yahoo.co.jp") || host.includes("valuecommerce.com")) return "yahoo";
  } catch {
    // not a parseable absolute URL - fall through
  }
  return "official";
}

/**
 * Records a real outbound shop-link click: fires the existing GA4 event
 * (same mechanism as every other trackEvent call - see lib/analytics.ts,
 * a no-op until NEXT_PUBLIC_GA_MEASUREMENT_ID is configured) and, in
 * parallel, a first-party copy to the backend (see
 * POST /api/track/affiliate-click, backend/app/models.py's AffiliateClick)
 * so the admin dashboard's click metrics never depend on the GA4 Data API
 * being configured. Both are best-effort and never block or affect the
 * actual navigation - a click that fails to record is still a real click.
 */
export function trackAffiliateClick({
  productId,
  category,
  shop,
  placement,
}: {
  productId?: number;
  category?: string;
  shop: Shop;
  placement: string;
}) {
  trackEvent("outbound_affiliate_click", {
    shop,
    placement,
    ...(productId !== undefined ? { product_id: productId } : {}),
    ...(category ? { category } : {}),
  });

  try {
    fetch(`${API_URL}/api/track/affiliate-click`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        product_id: productId ?? null,
        category: category ?? null,
        shop,
        placement,
      }),
      keepalive: true,
    }).catch(() => {
      // best-effort only - a dropped tracking request must never surface
      // to the visitor or block their click
    });
  } catch {
    // fetch itself can throw synchronously in rare environments - same
    // "never let tracking break the click" rule applies
  }
}
