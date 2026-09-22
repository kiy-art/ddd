// Amazon連携の第一段階（実績作りフェーズ）: PA-APIを使った価格取得は行わず、
// 商品名でAmazonの検索結果ページへ飛ばすだけのアフィリエイトリンクを生成する。
// 特定の商品ページへの直リンクではない（Amazon側に完全一致する商品が無い場合
// もあるため、検索結果に誘導する方が誤リンクにならず安全）。
//
// NEXT_PUBLIC_AMAZON_AFFILIATE_TAG が未設定の間はダミータグのままで、リンク
// 自体は生成されるが実際の紹介料には繋がらない（Amazonアソシエイトの審査には
// 直近180日で3件以上の紹介実績が必要なため、まずはこのリンクでクリックを
// 集めるところから始める設計）。
const DEFAULT_AMAZON_AFFILIATE_TAG = "par-jp-22";

export function getAmazonSearchUrl(productName: string): string {
  const tag = process.env.NEXT_PUBLIC_AMAZON_AFFILIATE_TAG || DEFAULT_AMAZON_AFFILIATE_TAG;
  const query = encodeURIComponent(productName);
  return `https://www.amazon.co.jp/s?k=${query}&tag=${encodeURIComponent(tag)}`;
}
