import TrackedCta from "@/components/TrackedCta";
import { getAmazonSearchUrl } from "@/lib/amazon";
import { Product } from "@/lib/api";

function yen(value: number | null): string {
  if (value === null) return "-";
  return `¥${value.toLocaleString("ja-JP")}`;
}

function storeLabel(url: string): string {
  try {
    const host = new URL(url).hostname;
    if (host.includes("rakuten.co.jp")) return "楽天市場";
    if (host.includes("amazon.co.jp") || host.includes("amazon.com")) return "Amazon";
    if (host.includes("yahoo.co.jp")) return "Yahoo!ショッピング";
  } catch {
    // fall through to the generic label below
  }
  return "販売ページ";
}

/**
 * Real price-source comparison, not a fabricated multi-store table. This
 * site currently tracks exactly one live price source per product (Rakuten
 * Ichiba, via rakuten.py) plus, when set, the manufacturer's own product
 * page (no price tracked there). Shipping fee/points/stock count aren't
 * collected at all, so those columns say "要確認" rather than a guessed
 * "送料無料" - see DataSourceNote for what's real vs. not yet connected.
 */
export default function StoreComparisonTable({
  product,
  lastUpdatedAt,
}: {
  product: Product;
  lastUpdatedAt: string | null;
}) {
  type Row = {
    label: string;
    price: number | null;
    priceDisplay?: string;
    url: string;
    isPriceSource: boolean;
    // Separate from isPriceSource: a search-result link (Amazon below) still
    // carries our affiliate tag and earns a commission on a resulting sale,
    // so it needs the same "sponsored" rel/disclosure treatment as a real
    // tracked price row even though it has no price to show.
    sponsored: boolean;
    updatedAt: string | null;
    detailNote?: string;
    ctaLabel?: string;
  };

  const rows: Row[] = [];
  if (product.affiliate_url) {
    rows.push({
      label: storeLabel(product.affiliate_url),
      price: product.current_price,
      url: product.affiliate_url,
      isPriceSource: true,
      sponsored: true,
      updatedAt: lastUpdatedAt,
    });
  }
  // Yahoo!ショッピング商品検索API - a real, independently-fetched second
  // price source (see app/yahoo.py), only shown when a match was actually
  // found for this specific product; never a fabricated row.
  if (product.yahoo_price !== null && product.yahoo_url) {
    rows.push({
      label: "Yahoo!ショッピング",
      price: product.yahoo_price,
      url: product.yahoo_url,
      isPriceSource: true,
      sponsored: true,
      updatedAt: product.yahoo_updated_at,
    });
  }
  if (product.product_url && product.product_url !== product.affiliate_url) {
    rows.push({
      label: "メーカー公式サイト",
      price: null,
      url: product.product_url,
      isPriceSource: false,
      sponsored: false,
      updatedAt: null,
    });
  }
  // Amazon: 実績作りフェーズ（PA-API未申請）につき価格は取得せず、商品名の
  // 検索結果ページへのリンクのみを表示する。特定商品への直リンクではない
  // ため、価格欄は空欄にし、文言でも「検索」であることを明記する。
  rows.push({
    label: "Amazon",
    price: null,
    priceDisplay: "-",
    url: getAmazonSearchUrl(product.name),
    isPriceSource: false,
    sponsored: true,
    updatedAt: null,
    detailNote: "商品名の検索結果ページが開きます",
    ctaLabel: "Amazonで探す →",
  });

  if (rows.length === 0) return null;

  const hasSponsoredRow = rows.some((row) => row.sponsored);
  const remainingStores = ["ゴルフ専門店"];

  return (
    <div className="rounded-2xl border border-border bg-card p-6 sm:p-8">
      <span className="text-xs font-medium uppercase tracking-[0.3em] text-accent">Store Comparison</span>
      <h2 className="mt-2 font-display text-2xl font-semibold text-foreground">販売価格を比較</h2>

      <div className="mt-5 overflow-x-auto">
        <table className="w-full min-w-[560px] border-collapse text-sm">
          <thead>
            <tr className="border-b border-border text-left text-[11px] uppercase tracking-widest text-foreground/40">
              <th className="pb-2 pr-4 font-medium">ショップ</th>
              <th className="pb-2 pr-4 font-medium">価格</th>
              <th className="pb-2 pr-4 font-medium">送料・ポイント・在庫</th>
              <th className="pb-2 pr-4 font-medium">更新日時</th>
              <th className="pb-2 font-medium"></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.url} className="border-b border-border last:border-0">
                <td className="py-3 pr-4 font-medium text-foreground">{row.label}</td>
                <td className="py-3 pr-4 font-display font-semibold text-foreground">
                  {row.priceDisplay ?? (row.isPriceSource ? yen(row.price) : "要確認")}
                </td>
                <td className="py-3 pr-4 text-xs text-foreground/40">
                  {row.detailNote ?? "販売ページでご確認ください"}
                </td>
                <td className="py-3 pr-4 text-xs text-foreground/40">
                  {row.updatedAt ? new Date(row.updatedAt).toLocaleString("ja-JP") : "-"}
                </td>
                <td className="py-3 text-right">
                  <TrackedCta
                    href={row.url}
                    target="_blank"
                    rel={row.sponsored ? "noopener noreferrer sponsored" : "noopener noreferrer"}
                    className="inline-block rounded-full border border-border px-4 py-1.5 text-xs font-semibold text-foreground/70 hover:border-brand/40 hover:text-brand"
                    event="cta_click"
                    params={{
                      product_id: product.id,
                      product_slug: product.slug,
                      product_name: product.name,
                      cta_type: row.isPriceSource ? "affiliate" : row.sponsored ? "affiliate_search" : "official",
                      buy_score: product.buy_score,
                    }}
                  >
                    {row.ctaLabel ?? "見る →"}
                  </TrackedCta>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="mt-4 text-xs text-foreground/35">
        {remainingStores.length > 0 && `${remainingStores.join("・")}の価格比較は現在準備中です。`}
        {hasSponsoredRow && (
          <>
            {" "}
            ※広告・PRを含みます。リンク経由の購入により当サイトが紹介料を受け取ることがあります。価格・在庫は変動するため、購入前に販売元サイトでご確認ください。
          </>
        )}
      </p>
    </div>
  );
}
