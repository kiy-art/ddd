// Yahoo!ショッピングの検索結果ページへのリンクを生成する。lib/amazon.tsと
// 同じ理由（商品名の完全一致が保証できないため、個別商品への直リンクより
// 検索結果への誘導が安全）に加えて、個別商品のアフィリエイトリンク
// （ValueCommerce経由、backend/app/yahoo.pyのto_affiliate_url）は「実際に
// 取得できた商品URL」に対してのみ有効な仕組みで、検索結果ページ自体を
// アフィリエイトラップする方式は未検証のため、このリンクは通常のURL
// （アフィリエイトタグなし・無報酬）とする。
export function getYahooSearchUrl(productName: string): string {
  const query = encodeURIComponent(productName);
  return `https://shopping.yahoo.co.jp/search?p=${query}`;
}
