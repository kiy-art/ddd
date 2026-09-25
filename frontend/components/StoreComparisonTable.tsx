import TrackedCta from "@/components/TrackedCta";
import { getAmazonSearchUrl } from "@/lib/amazon";
import { Product } from "@/lib/api";
import { getYahooSearchUrl } from "@/lib/yahoo";

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
 * site tracks two independent live price sources per product (Rakuten
 * Ichiba via rakuten.py, Yahoo!ショッピング via yahoo.py) plus, when set,
 * the manufacturer's own product page (no price tracked there). Shipping
 * fee/points/stock count aren't collected at all, so those columns say
 * "要確認" rather than a guessed "送料無料" - see DataSourceNote for
 * what's real vs. not yet connected.
 *
 * Rakuten/Yahoo/Amazon rows are always shown (never conditionally hidden)
 * so the table can't visually read as favoring whichever mall happens to
 * have a confirmed price today - Yahoo/Amazon fall back to an honest
 * "no confirmed price yet, here's a search link" row instead of
 * disappearing. Display order is sorted by price (cheapest first, unknown
 * last) rather than a fixed source order, for the same reason: which mall
 * leads the table should depend on today's actual prices, not on which
 * one this component happens to list first in code.
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
    // Separate from isPriceSource: a search-result link (Amazon/Yahoo
    // fallback below) can still carry our affiliate tag and earn a
    // commission on a resulting sale, so it needs the same "sponsored"
    // rel/disclosure treatment as a real tracked price row even though it
    // has no price to show.
    sponsored: boolean;
    // True for a row with no confirmed price where a real discount is
    // plausible (a third-party marketplace search) - gets a bolder CTA to
    // earn the click that would otherwise go to the price column. False
    // for the manufacturer's own page (typically fixed MSRP, so implying
    // "may be cheapest" there would be misleading).
    worthChecking: boolean;
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
      worthChecking: false,
      updatedAt: lastUpdatedAt,
    });
  }
  // Yahoo!ショッピング商品検索API - a real, independently-fetched second
  // price source (see app/yahoo.py). Always shown, same as every other row
  // here: when this product has no confirmed Yahoo match (or
  // YAHOO_CLIENT_ID isn't configured on the backend), it falls back to a
  // plain (non-affiliate - see lib/yahoo.ts) search link rather than
  // disappearing, so the table can't read as quietly dropping whichever
  // mall doesn't currently have data.
  if (product.yahoo_price !== null && product.yahoo_url) {
    rows.push({
      label: "Yahoo!ショッピング",
      price: product.yahoo_price,
      url: product.yahoo_url,
      isPriceSource: true,
      sponsored: true,
      worthChecking: false,
      updatedAt: product.yahoo_updated_at,
    });
  } else {
    rows.push({
      label: "Yahoo!ショッピング",
      price: null,
      priceDisplay: "-",
      url: getYahooSearchUrl(product.name),
      isPriceSource: false,
      sponsored: false,
      worthChecking: true,
      updatedAt: null,
      detailNote: "お得な出品が見つかる場合があります",
      ctaLabel: "Yahoo!ショッピングで価格をチェック →",
    });
  }
  if (product.product_url && product.product_url !== product.affiliate_url) {
    rows.push({
      label: "メーカー公式サイト",
      price: null,
      url: product.product_url,
      isPriceSource: false,
      sponsored: false,
      worthChecking: false,
      updatedAt: null,
      ctaLabel: "公式サイトを見る →",
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
    worthChecking: true,
    updatedAt: null,
    detailNote: "Amazon内の価格をチェック（最安値の可能性あり）",
    ctaLabel: "Amazonで最安値をチェック →",
  });

  if (rows.length === 0) return null;

  // Cheapest-first, unknown-price rows last - see the component docstring
  // for why this (not a fixed source order) is what keeps the table from
  // reading as favoring one mall.
  const displayRows = [...rows].sort((a, b) => (a.price ?? Infinity) - (b.price ?? Infinity));

  const hasSponsoredRow = rows.some((row) => row.sponsored);
  const remainingStores = ["ゴルフ専門店"];

  // Highlight the cheapest real price among actually-tracked sources
  // (Rakuten/Yahoo!) - only meaningful with 2+ real prices to compare, and
  // never involving the Amazon/official rows above, which have no price.
  const pricedRows = rows.filter((row): row is Row & { price: number } => row.isPriceSource && row.price !== null);
  const cheapestRow =
    pricedRows.length >= 2 ? pricedRows.reduce((min, row) => (row.price < min.price ? row : min)) : null;
  const priceDiff =
    cheapestRow && pricedRows.length >= 2
      ? Math.max(...pricedRows.map((row) => row.price)) - cheapestRow.price
      : null;

  return (
    <div className="rounded-2xl border border-border bg-card p-6 sm:p-8">
      <span className="text-xs font-medium uppercase tracking-[0.3em] text-accent">Store Comparison</span>
      <h2 className="mt-2 font-display text-2xl font-semibold text-foreground">販売価格を比較</h2>

      {cheapestRow && priceDiff !== null && priceDiff > 0 && (
        <p className="mt-3 rounded-xl bg-brand/10 px-3 py-2 text-sm font-semibold text-brand">
          現在は{cheapestRow.label}が最安です（他店との差額 {yen(priceDiff)}）
        </p>
      )}

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
            {displayRows.map((row) => (
              <tr key={row.url} className="border-b border-border last:border-0">
                <td className="py-3 pr-4 font-medium text-foreground">
                  {row.label}
                  {row === cheapestRow && (
                    <span className="ml-2 rounded-full bg-brand px-1.5 py-0.5 text-[9px] font-bold text-white">
                      最安
                    </span>
                  )}
                </td>
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
                    className={
                      row.worthChecking
                        ? "inline-block rounded-full bg-brand px-4 py-1.5 text-xs font-semibold text-white hover:bg-brand-dark"
                        : "inline-block rounded-full border border-border px-4 py-1.5 text-xs font-semibold text-foreground/70 hover:border-brand/40 hover:text-brand"
                    }
                    event="cta_click"
                    params={{
                      product_id: product.id,
                      product_slug: product.slug,
                      product_name: product.name,
                      cta_type: row.isPriceSource
                        ? "affiliate"
                        : row.sponsored
                          ? "affiliate_search"
                          : row.worthChecking
                            ? "marketplace_search"
                            : "official",
                      buy_score: product.buy_score,
                    }}
                    productId={product.id}
                    category={product.category}
                    placement="store_comparison"
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
