"use client";

import { detectShop, trackAffiliateClick } from "@/lib/affiliateTracking";
import { trackEvent } from "@/lib/analytics";

// cta_type values (see params.cta_type at each call site) that represent a
// real outbound click to a shop/marketplace, as opposed to an internal
// navigation or a non-commercial link - only these also get the
// first-party affiliate-click record (see trackAffiliateClick).
const AFFILIATE_CTA_TYPES = new Set(["affiliate", "affiliate_search", "affiliate_compare", "marketplace_search"]);

export default function TrackedCta({
  href,
  event,
  params,
  className,
  children,
  target,
  rel,
  productId,
  category,
  placement,
}: {
  href: string;
  event: string;
  params?: Record<string, string | number | boolean>;
  className?: string;
  children: React.ReactNode;
  target?: string;
  rel?: string;
  // Only needed on a shop/marketplace CTA (params.cta_type one of
  // AFFILIATE_CTA_TYPES) - omit on an internal or non-commercial link.
  productId?: number;
  category?: string;
  placement?: string;
}) {
  const handleClick = () => {
    trackEvent(event, params);
    const ctaType = params?.cta_type;
    if (placement && typeof ctaType === "string" && AFFILIATE_CTA_TYPES.has(ctaType)) {
      trackAffiliateClick({ productId, category, shop: detectShop(href), placement });
    }
  };

  return (
    <a href={href} target={target} rel={rel} className={className} onClick={handleClick}>
      {children}
    </a>
  );
}
