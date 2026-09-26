// Product structured data (JSON-LD) for /products/[slug].
//
// PAR. is a price-comparison / affiliate site: shoppers can't buy on
// par-gear.com, they click through to Rakuten / Yahoo!ショッピング. Google
// splits Product markup into two features:
//   - merchant listings: pages where the product is bought ON the site
//     (requires shipping/returns/seller details of that site), and
//   - product snippets: pages with product info that aggregate offers from
//     other sellers - which is what this page is.
// Search Console's "販売者のリスティング" report flagged pages that emitted a
// plain Offer (single price source) - Google read those as merchant
// listings. The offer is therefore always an AggregateOffer (1 or 2 real
// sources), which Google documents as not qualifying for merchant listings,
// so this page is evaluated as a product snippet.
//
// Deliberately NOT emitted: shippingDetails / hasMerchantReturnPolicy. PAR.
// ships nothing and accepts no returns, and each Rakuten/Yahoo shop has its
// own terms - any "default" policy here would be invented, and Google treats
// markup that misrepresents the page as a guideline violation. Same "never
// fabricate" rule as everywhere else on the site.

import type { ProductDetail } from "@/lib/api";
import { normalizeImageUrl } from "@/lib/imageUrl";

// sku must be a stable, unique, non-empty ASCII string. model_number is not
// that (shared across colour/loft variants, may be empty or contain spaces
// / full-width characters), so it goes to mpn instead - PAR.'s own product
// id is the one identifier guaranteed unique.
export function productSku(product: Pick<ProductDetail, "id">): string {
  return `PAR-${product.id}`;
}

function cleanIdentifier(value: string | null | undefined): string | null {
  if (typeof value !== "string") return null;
  // Whitespace first (tabs/newlines/full-width spaces become one space),
  // then drop any remaining control characters.
  const cleaned = value.replace(/\s+/g, " ").replace(/[\u0000-\u001f\u007f]/g, "").trim();
  return cleaned.length > 0 && cleaned.length <= 70 ? cleaned : null;
}

// The backend serializes datetimes as naive UTC ("2026-09-25T00:48:09", no
// designator - same issue app/sitemap.ts handles). A bare date-time isn't
// valid ISO 8601 with an offset, and JS would parse it as local time.
export function toIsoUtc(value: string | null | undefined): string | null {
  if (!value) return null;
  const hasTime = value.includes("T");
  const hasZone = /Z$|[+-]\d{2}:?\d{2}$/.test(value);
  const date = new Date(hasTime && !hasZone ? `${value}Z` : value);
  return Number.isNaN(date.getTime()) ? null : date.toISOString();
}

export function buildProductJsonLd({
  product,
  siteUrl,
  description,
  now = new Date(),
}: {
  product: ProductDetail;
  siteUrl: string;
  description: string;
  now?: Date;
}) {
  const pageUrl = `${siteUrl}/products/${product.slug}`;

  // image is required. The real product photo when there is a usable one;
  // otherwise this product's own generated share card
  // (app/products/[slug]/opengraph-image.tsx - 1200x630 PNG with the
  // product name and price, never an error), as a fully-qualified https URL.
  const photo = normalizeImageUrl(product.image_url);
  const image = photo
    ? photo.startsWith("/")
      ? `${siteUrl}${photo}`
      : photo
    : `${pageUrl}/opengraph-image`;

  const prices: number[] = [];
  if (product.current_price !== null) prices.push(product.current_price);
  if (product.yahoo_price !== null && product.yahoo_url) prices.push(product.yahoo_price);

  const lastRecordedAt =
    product.price_history.length > 0 ? product.price_history[product.price_history.length - 1].recorded_at : null;
  // validFrom: when this price was actually recorded (the last real price
  // fetch) - not "now", which would claim a price was checked at render
  // time when it wasn't.
  const validFrom = toIsoUtc(lastRecordedAt);
  // priceValidUntil: ~a week past that fetch, matching the daily refresh
  // cadence rather than overclaiming (unchanged from before).
  const validUntilBase = validFrom ? new Date(validFrom).getTime() : now.getTime();
  const priceValidUntil = new Date(validUntilBase + 7 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);

  const offers =
    prices.length > 0
      ? {
          "@type": "AggregateOffer",
          priceCurrency: "JPY",
          lowPrice: Math.min(...prices),
          highPrice: Math.max(...prices),
          offerCount: prices.length,
          ...(validFrom ? { validFrom } : {}),
          priceValidUntil,
          url: pageUrl,
        }
      : null;

  const mpn = cleanIdentifier(product.model_number);

  return {
    "@context": "https://schema.org",
    "@type": "Product",
    name: product.name,
    description,
    image: [image],
    sku: productSku(product),
    ...(mpn ? { mpn } : {}),
    brand: { "@type": "Brand", name: product.brand },
    url: pageUrl,
    ...(offers ? { offers } : {}),
  };
}
