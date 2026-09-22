// Amazon連携の第一段階（実績作りフェーズ）: PA-APIを使った価格取得は行わず、
// 商品名でAmazonの検索結果ページへ飛ばすだけのアフィリエイトリンクを生成する。
// 特定の商品ページへの直リンクではない（Amazon側に完全一致する商品が無い場合
// もあるため、検索結果に誘導する方が誤リンクにならず安全）。
//
// Amazonアソシエイトに実際に登録したトラッキングID（2026-09-22発行）。
// NEXT_PUBLIC_AMAZON_AFFILIATE_TAG を明示的に設定すればそちらが優先される
// ので、環境ごとに切り替えたい場合はそちらを使う。
const DEFAULT_AMAZON_AFFILIATE_TAG = "parjp-22";

export function getAmazonSearchUrl(productName: string): string {
  const tag = process.env.NEXT_PUBLIC_AMAZON_AFFILIATE_TAG || DEFAULT_AMAZON_AFFILIATE_TAG;
  const query = encodeURIComponent(productName);
  return `https://www.amazon.co.jp/s?k=${query}&tag=${encodeURIComponent(tag)}`;
}
