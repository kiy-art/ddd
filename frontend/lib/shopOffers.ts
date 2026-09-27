import type { Product } from "@/lib/api";

// STEP56: the shops with a real, recently fetched price for a product -
// Rakuten (current_price, the site's main tracked series) and Yahoo!
// (yahoo_price, fetched daily as a second source). The product page's top
// price, its main buy button and the store comparison table's "cheapest"
// note all read from here, so they can never disagree about which shop
// is cheapest.
//
// Only prices fetched within OFFER_FRESH_DAYS count: a Yahoo lookup that
// failed on a later day leaves the old yahoo_price in place, and an old
// price must not be presented as today's lowest. Amazon and the maker's
// own site have no price here at all (no price API - see
// StoreComparisonTable), so they are never part of "the lowest".

export const OFFER_FRESH_DAYS = 3;

export type ShopOffer = {
  shop: "rakuten" | "yahoo";
  label: string;
  price: number;
  url: string;
  updatedAt: string | null;
};

// The backend sends naive UTC timestamps ("2026-09-26T12:15:15").
function parseUtc(iso: string): number {
  const hasZone = /[zZ]|[+-]\d{2}:?\d{2}$/.test(iso);
  return new Date(hasZone ? iso : `${iso}Z`).getTime();
}

function isFresh(iso: string | null, now: number): boolean {
  if (!iso) return false;
  const t = parseUtc(iso);
  return !Number.isNaN(t) && now - t <= OFFER_FRESH_DAYS * 24 * 60 * 60 * 1000;
}

export function getShopOffers(
  product: Pick<Product, "current_price" | "affiliate_url" | "yahoo_price" | "yahoo_url" | "yahoo_updated_at">,
  rakutenUpdatedAt: string | null,
  now: number = Date.now()
): ShopOffer[] {
  const offers: ShopOffer[] = [];
  if (
    product.current_price !== null &&
    product.affiliate_url &&
    product.affiliate_url.includes("rakuten.co.jp") &&
    isFresh(rakutenUpdatedAt, now)
  ) {
    offers.push({
      shop: "rakuten",
      label: "楽天市場",
      price: product.current_price,
      url: product.affiliate_url,
      updatedAt: rakutenUpdatedAt,
    });
  }
  if (product.yahoo_price !== null && product.yahoo_url && isFresh(product.yahoo_updated_at, now)) {
    offers.push({
      shop: "yahoo",
      label: "Yahoo!ショッピング",
      price: product.yahoo_price,
      url: product.yahoo_url,
      updatedAt: product.yahoo_updated_at,
    });
  }
  return offers.sort((a, b) => a.price - b.price);
}

// The cheapest fresh offer, or null when no shop has a recent price.
export function getLowestOffer(offers: ShopOffer[]): ShopOffer | null {
  return offers[0] ?? null;
}
