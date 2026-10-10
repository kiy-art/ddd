// Yahoo!ショッピングの検索結果ページへのリンクを生成する。lib/amazon.tsと
// 同じ理由（商品名の完全一致が保証できないため、個別商品への直リンクより
// 検索結果への誘導が安全）。
//
// STEP67: ValueCommerceのMyLink（sid＝サイトID、pid＝Yahoo!ショッピング
// 広告のID）が両方設定されていれば、検索結果ページもMyLinkで包んで
// 紹介料の対象にする（MyLinkは広告主ドメイン内の任意ページを遷移先にできる）。
// どちらかが空なら従来どおり通常のURL（アフィリエイトタグなし）。
// 個別商品のリンクはバックエンド（backend/app/yahoo.pyのto_affiliate_url）が
// 同じsid/pidで包む。どちらの値もリンクに必ず表示される公開情報。
//
// 2026-10-10: バリューコマースで実際に発行された番号（2026-10-06取得、受信箱
// TK-3）を既定値にした。lib/amazon.tsと同じく、環境変数を明示的に設定すれば
// そちらが優先される。
const DEFAULT_VC_SID = "3782576";
const DEFAULT_VC_PID = "892721752";
const VC_SID = process.env.NEXT_PUBLIC_VC_SID?.trim() || DEFAULT_VC_SID;
const VC_PID = process.env.NEXT_PUBLIC_VC_PID?.trim() || DEFAULT_VC_PID;

export const YAHOO_SEARCH_IS_AFFILIATE = VC_SID !== "" && VC_PID !== "";

export function getYahooSearchUrl(productName: string): string {
  const query = encodeURIComponent(productName);
  const searchUrl = `https://shopping.yahoo.co.jp/search?p=${query}`;
  if (!YAHOO_SEARCH_IS_AFFILIATE) return searchUrl;
  return (
    "https://ck.jp.ap.valuecommerce.com/servlet/referral" +
    `?sid=${encodeURIComponent(VC_SID)}&pid=${encodeURIComponent(VC_PID)}&vc_url=${encodeURIComponent(searchUrl)}`
  );
}
