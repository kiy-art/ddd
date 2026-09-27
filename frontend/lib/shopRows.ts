import { getAmazonSearchUrl } from "@/lib/amazon";
import type { Product } from "@/lib/api";
import { getLowestOffer, getShopOffers, parseUtc, type ShopOffer } from "@/lib/shopOffers";
import { getYahooSearchUrl } from "@/lib/yahoo";

// STEP57: every shop link on the product page - the hero's buy buttons and
// the store comparison board - is built from this one list, so both always
// show the same shops, prices, "最安" marker and tracking.
//
// Only Rakuten and Yahoo! have a real fetched price (lib/shopOffers.ts).
// Amazon and Yahoo! without a matched listing are search links, the maker
// site is a plain link - those rows never show a price or "最安".

export type ShopKey = "rakuten" | "yahoo" | "amazon" | "official" | "other";

export type ShopRow = {
  key: ShopKey;
  label: string;
  url: string;
  price: number | null;
  // "price": a fetched listing price. "search": a shop search-results page.
  // "official": the maker's own page (usually list price).
  kind: "price" | "search" | "official";
  sponsored: boolean;
  updatedAt: string | null;
  isLowest: boolean;
  note: string;
  cta: string;
  ctaType: "affiliate" | "affiliate_search" | "marketplace_search" | "official";
};

function shopOf(url: string): { key: ShopKey; label: string } {
  try {
    const host = new URL(url).hostname;
    if (host.includes("rakuten.co.jp")) return { key: "rakuten", label: "楽天市場" };
    if (host.includes("amazon.co.jp") || host.includes("amazon.com")) return { key: "amazon", label: "Amazon" };
    if (host.includes("yahoo.co.jp") || host.includes("valuecommerce.com")) return { key: "yahoo", label: "Yahoo!ショッピング" };
  } catch {
    // not a parseable URL - generic label below
  }
  return { key: "other", label: "販売ページ" };
}

export function formatUpdatedAt(iso: string | null): string | null {
  if (!iso) return null;
  const t = parseUtc(iso);
  if (Number.isNaN(t)) return null;
  return new Date(t).toLocaleString("ja-JP", {
    timeZone: "Asia/Tokyo",
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export type ShopBoard = {
  rows: ShopRow[];
  // Set only when 2+ shops have a fresh price - one known price isn't
  // "the lowest" of anything.
  lowest: ShopOffer | null;
  // How much more the other priced shop(s) charge, at most.
  savings: number | null;
};

export function buildShopBoard(product: Product, rakutenUpdatedAt: string | null): ShopBoard {
  const offers = getShopOffers(product, rakutenUpdatedAt);
  const lowest = offers.length >= 2 ? getLowestOffer(offers) : null;
  const savings = lowest ? Math.max(...offers.map((o) => o.price)) - lowest.price : null;

  const priced: ShopRow[] = [];
  const links: ShopRow[] = [];

  if (product.affiliate_url) {
    const shop = shopOf(product.affiliate_url);
    priced.push({
      ...shop,
      url: product.affiliate_url,
      price: product.current_price,
      kind: "price",
      sponsored: true,
      updatedAt: rakutenUpdatedAt,
      isLowest: false,
      note: "",
      cta: `${shop.label}で見る`,
      ctaType: "affiliate",
    });
  }
  if (product.yahoo_price !== null && product.yahoo_url) {
    priced.push({
      key: "yahoo",
      label: "Yahoo!ショッピング",
      url: product.yahoo_url,
      price: product.yahoo_price,
      kind: "price",
      sponsored: true,
      updatedAt: product.yahoo_updated_at,
      isLowest: false,
      note: "",
      cta: "Yahoo!ショッピングで見る",
      ctaType: "affiliate",
    });
  }
  // Amazon: no price API yet (PA-API needs sales history first) - a tagged
  // search link, always shown so the board never reads as leaving it out.
  links.push({
    key: "amazon",
    label: "Amazon",
    url: getAmazonSearchUrl(product.name),
    price: null,
    kind: "search",
    sponsored: true,
    updatedAt: null,
    isLowest: false,
    note: "Amazonでの販売価格を確認できます",
    cta: "Amazonで価格をチェック",
    ctaType: "affiliate_search",
  });
  if (!(product.yahoo_price !== null && product.yahoo_url)) {
    links.push({
      key: "yahoo",
      label: "Yahoo!ショッピング",
      url: getYahooSearchUrl(product.name),
      price: null,
      kind: "search",
      sponsored: false, // plain search URL, no affiliate tag (lib/yahoo.ts)
      updatedAt: null,
      isLowest: false,
      note: "出品一覧から価格を確認できます",
      cta: "Yahoo!で価格をチェック",
      ctaType: "marketplace_search",
    });
  }
  if (product.product_url && product.product_url !== product.affiliate_url) {
    links.push({
      key: "official",
      label: "メーカー公式サイト",
      url: product.product_url,
      price: null,
      kind: "official",
      sponsored: false,
      updatedAt: null,
      isLowest: false,
      note: "メーカーの商品ページ（価格は販売店と異なる場合があります）",
      cta: "公式サイトを見る",
      ctaType: "official",
    });
  }

  for (const row of priced) {
    row.isLowest = lowest !== null && row.url === lowest.url;
  }
  priced.sort((a, b) => (a.price ?? Infinity) - (b.price ?? Infinity));
  return { rows: [...priced, ...links], lowest, savings };
}

export const SHOP_MARKS: Record<ShopKey, { glyph: string; className: string }> = {
  rakuten: { glyph: "楽", className: "bg-[#bf0000] text-white" },
  yahoo: { glyph: "Y!", className: "bg-[#ff0033] text-white" },
  amazon: { glyph: "a", className: "bg-[#131921] text-[#ff9900]" },
  official: { glyph: "公", className: "bg-foreground/10 text-foreground/60" },
  other: { glyph: "店", className: "bg-foreground/10 text-foreground/60" },
};
