import CtaArrow from "@/components/CtaArrow";
import TrackedCta from "@/components/TrackedCta";
import { Product } from "@/lib/api";
import { SHOP_MARKS, ShopRow, buildShopBoard, formatUpdatedAt, staleLabel } from "@/lib/shopRows";

function yen(value: number | null): string {
  if (value === null) return "-";
  return `¥${value.toLocaleString("ja-JP")}`;
}

/**
 * STEP57 "shop price board" - sits directly under the product summary, so
 * "where is it cheapest, and take me there" is the first thing after the
 * product itself.
 *
 * Real price sources only (lib/shopOffers.ts): Rakuten and Yahoo! show
 * their fetched price; Amazon / Yahoo! without a matched listing are search
 * links; the maker site is a plain link. When 2+ shops have a fresh price,
 * the cheapest gets the mint "winner" banner with the page's biggest
 * button - which shop that is depends only on today's prices, never on a
 * fixed order in code. Shipping/points/stock aren't collected, so nothing
 * here claims them.
 */
export default function StoreComparisonTable({
  product,
  lastUpdatedAt,
}: {
  product: Product;
  lastUpdatedAt: string | null;
}) {
  const { rows, lowest, savings } = buildShopBoard(product, lastUpdatedAt);
  if (rows.length === 0) return null;

  // STEP74: only shops whose price is fresh count as "compared daily".
  const pricedCount = rows.filter((row) => row.kind === "price" && row.price !== null && !row.stale).length;
  const lowestRow = rows.find((row) => row.isLowest) ?? null;
  const hasSponsoredRow = rows.some((row) => row.sponsored);

  const track = (row: ShopRow, placement: string) => ({
    event: "cta_click",
    params: {
      product_id: product.id,
      product_slug: product.slug,
      product_name: product.name,
      cta_type: row.ctaType,
      shop: row.key,
      buy_score: product.buy_score,
    },
    productId: product.id,
    category: product.category,
    placement,
  });

  return (
    <div className="card-lux overflow-hidden rounded-3xl">
      <div className="flex flex-wrap items-end justify-between gap-3 px-6 pt-6 sm:px-8 sm:pt-8">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium uppercase tracking-[0.3em] text-accent">Store Comparison</span>
            <span className="rounded border border-foreground/30 px-1.5 py-0.5 text-[11px] font-semibold text-foreground/70">PR</span>
          </div>
          <h2 className="mt-2 font-display text-2xl font-semibold text-foreground sm:text-3xl">販売価格を比較</h2>
        </div>
        <p className="text-xs text-foreground/65">
          {pricedCount >= 2 ? `${pricedCount}店舗の最新価格を比較` : "価格は1日1回取得"}・{rows.length}ショップを掲載
        </p>
      </div>

      {/* Winner banner (mint, STEP60): the cheapest fetched price, with the page's
          biggest button. Only when there really is a comparison. */}
      {lowest && lowestRow && (
        <div className="terminal-panel relative mx-4 mt-5 overflow-hidden rounded-2xl border border-brand/25 px-5 py-5 sm:mx-6 sm:px-7 sm:py-6">
          <div className="relative flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-4">
              <ShopMark row={lowestRow} size="lg" />
              <div>
                <span className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.2em] text-brand">
                  <span className="live-dot" aria-hidden="true" />
                  比較した中で価格が低いショップ
                </span>
                <div className="mt-1 flex flex-wrap items-baseline gap-x-3">
                  <span className="font-display text-lg font-semibold text-foreground">{lowestRow.label}</span>
                  <span className="font-num text-3xl font-semibold text-brand sm:text-4xl">{yen(lowest.price)}</span>
                </div>
                {formatUpdatedAt(lowestRow.updatedAt) && (
                  <span className="block text-xs text-foreground/65">{formatUpdatedAt(lowestRow.updatedAt)} 時点の価格</span>
                )}
                {savings !== null && savings > 0 && (
                  <span className="text-xs text-foreground/60">
                    比較した他店との差は最大 <span className="font-num font-semibold text-foreground">{yen(savings)}</span>
                  </span>
                )}
              </div>
            </div>
            <TrackedCta
              href={lowestRow.url}
              target="_blank"
              rel="noopener noreferrer sponsored"
              className="btn-shop tap w-full shrink-0 whitespace-nowrap rounded-full px-6 py-4 text-sm font-semibold sm:w-auto sm:px-7 sm:text-base"
              {...track(lowestRow, "store_comparison_top")}
            >
              {lowestRow.label}で買う
              <CtaArrow />
            </TrackedCta>
          </div>
        </div>
      )}

      <ul className="mt-5 flex flex-col gap-2 px-4 pb-4 sm:px-6">
        {rows.map((row) => (
          <li
            key={`${row.key}-${row.url}`}
            className={`flex flex-col gap-3 rounded-2xl border p-4 sm:flex-row sm:items-center sm:gap-5 ${
              row.isLowest
                ? "border-brand/50 bg-brand/[0.05] shadow-[0_0_0_1px_rgba(var(--glow),0.25)]"
                : "border-border bg-background"
            }`}
          >
            <div className="flex min-w-0 flex-1 items-center gap-3">
              <ShopMark row={row} />
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-semibold text-foreground">{row.label}</span>
                  {row.isLowest && (
                    <span className="rounded-full bg-brand px-2 py-0.5 text-[10px] font-bold text-on-brand">価格が低い</span>
                  )}
                </div>
                <span className="text-xs text-foreground/65">
                  {row.kind === "price"
                    ? row.stale
                      ? `${staleLabel(row)}${formatUpdatedAt(row.updatedAt) ? `（${formatUpdatedAt(row.updatedAt)} 時点）` : ""}・最新は販売ページで確認`
                      : formatUpdatedAt(row.updatedAt)
                        ? `${formatUpdatedAt(row.updatedAt)} 時点・送料/ポイントは販売ページで確認`
                        : "送料/ポイントは販売ページで確認"
                    : row.note}
                </span>
              </div>
            </div>

            <div className="flex items-center justify-between gap-4 sm:justify-end">
              <span
                className={`shrink-0 font-num text-xl font-semibold sm:w-28 sm:text-right ${
                  row.isLowest
                    ? "text-brand dark:text-brand-light"
                    : row.price !== null && !row.stale
                      ? "text-foreground"
                      : "text-foreground/65"
                }`}
              >
                {row.kind === "price" ? yen(row.price) : "—"}
                {lowest && !row.isLowest && !row.stale && row.kind === "price" && row.price !== null && row.price > lowest.price && (
                  <span className="block text-xs font-normal text-foreground/65">
                    差額 +{yen(row.price - lowest.price)}
                  </span>
                )}
              </span>
              <TrackedCta
                href={row.url}
                target="_blank"
                rel={row.sponsored ? "noopener noreferrer sponsored" : "noopener noreferrer"}
                className={`tap inline-flex min-w-0 flex-1 items-center justify-center gap-1.5 whitespace-nowrap rounded-full px-4 py-3 text-[13px] font-semibold sm:min-w-[11rem] sm:flex-none sm:px-5 sm:text-sm ${
                  row.isLowest || (row.kind === "search" && row.sponsored && row.key !== "alpen")
                    ? "btn-shop"
                    : "btn-ghost text-foreground/80 hover:text-foreground"
                }`}
                {...track(row, "store_comparison")}
              >
                {row.cta}
                <CtaArrow className="h-3.5 w-3.5" />
              </TrackedCta>
            </div>
          </li>
        ))}
      </ul>

      <p className="border-t border-border px-6 py-4 text-sm leading-relaxed text-foreground/80 sm:px-8">
        価格はPAR.が取得した各ショップの価格です（楽天市場は1日1回、Yahoo!ショッピングは取得できた時点）。取得から3日を過ぎた価格は「◯日前の価格」と表示し、最安の比較には含めません（Amazonは価格未取得のため検索結果へのリンク、ゴルフ5・アルペンは価格未取得のためストアのトップへのリンク）。
        {hasSponsoredRow &&
          "※広告・PRを含みます。リンク経由の購入により当サイトが紹介料を受け取ることがあります。"}
        価格・在庫は変動するため、購入前に販売元サイトでご確認ください。
      </p>
      {rows.some((row) => row.key === "alpen") && (
        // ValueCommerce's impression counter for the ゴルフ5・アルペン link (program 2145165).
        // eslint-disable-next-line @next/next/no-img-element
        <img src="https://ad.jp.ap.valuecommerce.com/servlet/gifbanner?sid=3782576&pid=892736409" width={1} height={1} alt="" className="block h-px w-px" />
      )}
    </div>
  );
}

function ShopMark({ row, size = "md" }: { row: ShopRow; size?: "md" | "lg" }) {
  const mark = SHOP_MARKS[row.key];
  return (
    <span
      aria-hidden="true"
      className={`flex shrink-0 items-center justify-center rounded-xl font-bold ${mark.className} ${
        size === "lg" ? "h-12 w-12 text-lg" : "h-10 w-10 text-sm"
      }`}
    >
      {mark.glyph}
    </span>
  );
}
