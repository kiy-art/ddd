import type { Product } from "@/lib/api";

// STEP68: the product page's <title> and meta description.
//
// Title: 「【{年}年最新】{ブランド 商品名} の{訴求} | PAR. AIゴルフアナリティクス」.
// The year is the current year in Japan, never a hard-coded one, and
// "最新" refers to the page's price data, which is refreshed daily.
// {訴求} follows the page's real search intent once the daily optimizer
// has read it from Search Console (backend app/seo_intent.py ->
// product.seo_title_intent); every phrase names something the page
// really has. Unknown/missing keys fall back to the default phrase.
export const SEO_TITLE_PHRASES: Record<string, string> = {
  price: "買い時・最安値比較",
  timing: "買い時・値下がり予測",
  spec: "スペック・価格比較",
};
const DEFAULT_PHRASE = SEO_TITLE_PHRASES.price;
export const SEO_TITLE_SUFFIX = "PAR. AIゴルフアナリティクス";

function jstYear(now: Date): number {
  return new Date(now.getTime() + 9 * 60 * 60 * 1000).getUTCFullYear();
}

// "TaylorMade Qi35 ドライバー" - the brand is what most searches start
// with, so it leads unless the stored name already contains it.
export function productDisplayName(product: Pick<Product, "brand" | "name">): string {
  const name = product.name.trim();
  const brand = product.brand.trim();
  if (!brand || name.toLowerCase().includes(brand.toLowerCase())) return name;
  return `${brand} ${name}`;
}

export function productSeoTitle(
  product: Pick<Product, "brand" | "name" | "seo_title_intent">,
  now: Date = new Date()
): string {
  const phrase = (product.seo_title_intent && SEO_TITLE_PHRASES[product.seo_title_intent]) || DEFAULT_PHRASE;
  return `【${jstYear(now)}年最新】${productDisplayName(product)} の${phrase} | ${SEO_TITLE_SUFFIX}`;
}

// Only what the page really offers: prices are fetched daily (not in real
// time) from Rakuten and Yahoo!ショッピング; Amazon is a search link with no
// fetched price, so it isn't named as a price source here.
export function productSeoDescription(product: Pick<Product, "brand" | "name">): string {
  return (
    "過去の価格推移データからAIが今買うべきか判定。" +
    `${productDisplayName(product)} の楽天市場・Yahoo!ショッピングの最安値と割引率を毎日比較。`
  );
}
