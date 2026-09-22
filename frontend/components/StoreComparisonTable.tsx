import TrackedCta from "@/components/TrackedCta";
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
  const rows: { label: string; price: number | null; url: string; isPriceSource: boolean }[] = [];
  if (product.affiliate_url) {
    rows.push({
      label: storeLabel(product.affiliate_url),
      price: product.current_price,
      url: product.affiliate_url,
      isPriceSource: true,
    });
  }
  if (product.product_url && product.product_url !== product.affiliate_url) {
    rows.push({ label: "メーカー公式サイト", price: null, url: product.product_url, isPriceSource: false });
  }

  if (rows.length === 0) return null;

  return (
    <div className="rounded-2xl border border-border bg-card p-6 sm:p-8">
      <span className="text-xs font-medium uppercase tracking-[0.3em] text-accent">Store Comparison</span>
      <h2 className="mt-2 font-display text-2xl font-semibold text-foreground">販売価格を比較</h2>
      {lastUpdatedAt && (
        <p className="mt-1 text-xs text-foreground/40">
          最終更新：{new Date(lastUpdatedAt).toLocaleString("ja-JP")}
        </p>
      )}

      <div className="mt-5 overflow-x-auto">
        <table className="w-full min-w-[480px] border-collapse text-sm">
          <thead>
            <tr className="border-b border-border text-left text-[11px] uppercase tracking-widest text-foreground/40">
              <th className="pb-2 pr-4 font-medium">ショップ</th>
              <th className="pb-2 pr-4 font-medium">価格</th>
              <th className="pb-2 pr-4 font-medium">送料・ポイント・在庫</th>
              <th className="pb-2 font-medium"></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.url} className="border-b border-border last:border-0">
                <td className="py-3 pr-4 font-medium text-foreground">{row.label}</td>
                <td className="py-3 pr-4 font-display font-semibold text-foreground">
                  {row.isPriceSource ? yen(row.price) : "要確認"}
                </td>
                <td className="py-3 pr-4 text-xs text-foreground/40">販売ページでご確認ください</td>
                <td className="py-3 text-right">
                  <TrackedCta
                    href={row.url}
                    target="_blank"
                    rel={row.isPriceSource ? "noopener noreferrer sponsored" : "noopener noreferrer"}
                    className="inline-block rounded-full border border-border px-4 py-1.5 text-xs font-semibold text-foreground/70 hover:border-brand/40 hover:text-brand"
                    event="cta_click"
                    params={{
                      product_id: product.id,
                      product_slug: product.slug,
                      product_name: product.name,
                      cta_type: row.isPriceSource ? "affiliate" : "official",
                      buy_score: product.buy_score,
                    }}
                  >
                    見る →
                  </TrackedCta>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="mt-4 text-xs text-foreground/35">
        Amazon・Yahoo!ショッピング・ゴルフ専門店の価格比較は現在準備中です。
        {product.affiliate_url && (
          <>
            {" "}
            ※広告・PRを含みます。リンク経由の購入により当サイトが紹介料を受け取ることがあります。価格・在庫は変動するため、購入前に販売元サイトでご確認ください。
          </>
        )}
      </p>
    </div>
  );
}
