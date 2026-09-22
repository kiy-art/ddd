import type { Metadata } from "next";
import Link from "next/link";

import AiBuySignal from "@/components/AiBuySignal";
import CategoryIcon from "@/components/CategoryIcon";
import RemoveFromCompareButton from "@/components/RemoveFromCompareButton";
import SafeProductImage from "@/components/SafeProductImage";
import TrackedCta from "@/components/TrackedCta";
import { ProductDetail, getProduct } from "@/lib/api";
import { MAX_COMPARE } from "@/lib/compare";
import { forecastMonthLabel } from "@/lib/forecast";

export const revalidate = 0;

const THIN_DATA_DAYS = 7;

export const metadata: Metadata = {
  title: "商品比較",
  description: "選択したゴルフ用品を価格・買い時スコア・価格予測で比較できます。",
};

function yen(value: number | null): string {
  if (value === null) return "-";
  return `¥${value.toLocaleString("ja-JP")}`;
}

function ctaLabel(url: string): string {
  try {
    const host = new URL(url).hostname;
    if (host.includes("rakuten.co.jp")) return "楽天市場で見る";
    if (host.includes("amazon.co.jp") || host.includes("amazon.com")) return "Amazonで見る";
  } catch {
    // fall through
  }
  return "価格を見る";
}

async function loadProducts(slugs: string[]): Promise<ProductDetail[]> {
  const results = await Promise.allSettled(slugs.map((slug) => getProduct(slug)));
  return results
    .filter((r): r is PromiseFulfilledResult<ProductDetail> => r.status === "fulfilled")
    .map((r) => r.value);
}

export default async function ComparePage({
  searchParams,
}: {
  searchParams: Promise<{ slugs?: string }>;
}) {
  const { slugs: slugsParam } = await searchParams;
  const slugs = (slugsParam ?? "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean)
    .slice(0, MAX_COMPARE);

  const products = slugs.length > 0 ? await loadProducts(slugs) : [];

  return (
    <div>
      <section className="bg-ink px-6 py-20 text-white sm:py-28">
        <div className="mx-auto max-w-7xl">
          <span className="text-xs font-medium uppercase tracking-[0.3em] text-accent">Compare</span>
          <h1 className="mt-3 font-display text-4xl font-semibold leading-tight sm:text-5xl">商品比較</h1>
          <p className="mt-3 text-sm text-white/70">
            価格・買い時スコア・価格予測を並べて比較できます（最大{MAX_COMPARE}商品）。
          </p>
        </div>
      </section>

      <section className="px-6 py-16 sm:py-20">
        <div className="mx-auto max-w-7xl">
          {products.length < 2 ? (
            <div className="rounded-2xl border border-dashed border-border bg-card px-6 py-16 text-center">
              <p className="text-sm text-foreground/60">
                比較するには2商品以上が必要です。各商品ページやカードの「＋比較」ボタンから追加してください。
              </p>
              <Link
                href="/"
                className="mt-6 inline-block rounded-full bg-brand px-6 py-3 text-sm font-semibold text-white transition-transform hover:scale-[1.02]"
              >
                商品を探す →
              </Link>
            </div>
          ) : (
            <div className="w-full overflow-x-auto">
              <table className="w-full min-w-[640px] border-separate border-spacing-0">
                <thead>
                  <tr>
                    <th className="w-32 sm:w-44" />
                    {products.map((p) => (
                      <th key={p.id} className="w-1/4 min-w-[180px] px-3 pb-6 text-left align-top">
                        <div className="flex flex-col gap-3">
                          <div className="relative flex aspect-square w-full items-center justify-center overflow-hidden rounded-xl border border-border bg-card">
                            {p.image_url ? (
                              <SafeProductImage src={p.image_url} alt={p.name} category={p.category} className="object-contain p-4" />
                            ) : (
                              <CategoryIcon category={p.category} />
                            )}
                          </div>
                          <div>
                            <Link
                              href={`/products/${p.slug}`}
                              className="line-clamp-2 font-display text-sm font-medium leading-snug text-foreground hover:text-brand"
                            >
                              {p.name}
                            </Link>
                            <p className="mt-1 text-[11px] uppercase tracking-widest text-foreground/40">{p.brand}</p>
                          </div>
                          <RemoveFromCompareButton slug={p.slug} />
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="text-sm">
                  <CompareRow label="現在価格">
                    {products.map((p) => (
                      <td key={p.id} className="px-3 py-4 font-display text-lg font-semibold text-foreground">
                        {yen(p.current_price)}
                      </td>
                    ))}
                  </CompareRow>

                  <CompareRow label="30日平均">
                    {products.map((p) => {
                      const reliable = p.buy_score !== "insufficient_data" && p.history_span_days >= THIN_DATA_DAYS;
                      return (
                        <td key={p.id} className="px-3 py-4 text-foreground/70">
                          {reliable ? yen(p.average_price) : `蓄積中（${p.history_span_days}日分）`}
                        </td>
                      );
                    })}
                  </CompareRow>

                  <CompareRow label="値下がり率">
                    {products.map((p) => {
                      const reliable = p.buy_score !== "insufficient_data" && p.history_span_days >= THIN_DATA_DAYS;
                      const pct = reliable ? p.price_change_percent : null;
                      return (
                        <td
                          key={p.id}
                          className={`px-3 py-4 font-semibold ${pct !== null && pct < 0 ? "text-sale" : "text-foreground/60"}`}
                        >
                          {pct === null ? "-" : `${pct > 0 ? "+" : ""}${pct}%`}
                        </td>
                      );
                    })}
                  </CompareRow>

                  <CompareRow label="買い時スコア">
                    {products.map((p) => (
                      <td key={p.id} className="px-3 py-4">
                        <AiBuySignal
                          buyScore={p.buy_score}
                          buySignalScore={p.buy_signal_score}
                          historySpanDays={p.history_span_days}
                          size="sm"
                        />
                      </td>
                    ))}
                  </CompareRow>

                  <CompareRow label="🔮 予測価格">
                    {products.map((p) => (
                      <td key={p.id} className="px-3 py-4 text-accent-dark">
                        {p.forecast_low_price !== null && p.forecast_high_price !== null
                          ? `${yen(p.forecast_low_price)}〜${yen(p.forecast_high_price)}`
                          : "予測情報なし"}
                      </td>
                    ))}
                  </CompareRow>

                  <CompareRow label="🔮 予測時期">
                    {products.map((p) => (
                      <td key={p.id} className="px-3 py-4 text-foreground/70">
                        {p.forecast_target_date ? forecastMonthLabel(p.forecast_target_date) : "-"}
                      </td>
                    ))}
                  </CompareRow>

                  <CompareRow label="" last>
                    {products.map((p) => (
                      <td key={p.id} className="px-3 py-6 align-top">
                        {p.affiliate_url ? (
                          <TrackedCta
                            href={p.affiliate_url}
                            target="_blank"
                            rel="noopener noreferrer sponsored"
                            className="block w-full rounded-full bg-brand px-4 py-3 text-center text-xs font-semibold text-white transition-transform hover:scale-[1.03]"
                            event="cta_click"
                            params={{ product_id: p.id, product_slug: p.slug, cta_type: "affiliate_compare" }}
                          >
                            {ctaLabel(p.affiliate_url)}
                          </TrackedCta>
                        ) : (
                          <Link
                            href={`/products/${p.slug}`}
                            className="block w-full rounded-full border border-border px-4 py-3 text-center text-xs font-semibold text-foreground/70 hover:border-brand/40 hover:text-brand"
                          >
                            詳細を見る
                          </Link>
                        )}
                      </td>
                    ))}
                  </CompareRow>
                </tbody>
              </table>
              <p className="mt-4 text-xs text-foreground/35">
                ※「🔮」の付いた項目は過去の価格データをもとにした予測であり、将来価格を保証するものではありません。
              </p>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

function CompareRow({ label, children, last }: { label: string; children: React.ReactNode; last?: boolean }) {
  return (
    <tr className={last ? "" : "border-b border-border"}>
      <th scope="row" className="w-32 px-3 py-4 text-left text-xs font-medium text-foreground/45 sm:w-44">
        {label}
      </th>
      {children}
    </tr>
  );
}
