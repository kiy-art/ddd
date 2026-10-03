import Link from "next/link";

import AiBuySignal from "@/components/AiBuySignal";
import RemoveFromCompareButton from "@/components/RemoveFromCompareButton";
import SafeProductImage from "@/components/SafeProductImage";
import TrackedCta from "@/components/TrackedCta";
import { getAmazonSearchUrl } from "@/lib/amazon";
import type { ProductDetail } from "@/lib/api";
import { PERFORMANCE_TYPE_LABELS, SKILL_LEVEL_LABELS } from "@/lib/badges";
import { forecastMonthLabel } from "@/lib/forecast";
import { SPEC_ORDER } from "@/lib/productSpecs";

// The side-by-side comparison table - /compare (the visitor's own list,
// removable) and the STEP69 "A vs B" pages (/compare/[pair]).

const THIN_DATA_DAYS = 7;

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

export default function CompareTable({
  products,
  removable = false,
  placement = "compare_table",
}: {
  products: ProductDetail[];
  removable?: boolean;
  placement?: string;
}) {
  // Spec rows shown = specs at least one compared product has.
  const specKeys = SPEC_ORDER.filter(({ key }) => products.some((p) => p.specs?.[key]));
  return (
            <div className="w-full overflow-x-auto">
              <table className="w-full min-w-[640px] border-separate border-spacing-0">
                <thead>
                  <tr>
                    <th className="w-32 sm:w-44" />
                    {products.map((p) => (
                      <th key={p.id} className="w-1/4 min-w-[180px] px-3 pb-6 text-left align-top">
                        <div className="flex flex-col gap-3">
                          <div className="relative flex aspect-square w-full items-center justify-center overflow-hidden rounded-xl border border-border bg-card">
                            <SafeProductImage src={p.image_url} alt={p.name} category={p.category} className="object-contain p-4" compact />
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
                          {removable && <RemoveFromCompareButton slug={p.slug} />}
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="text-sm">
                  {/* STEP61: what the clubs ARE, before what they cost -
                      maker positioning (researched) and seller-stated specs. */}
                  <CompareRow label="対象レベル">
                    {products.map((p) => (
                      <td key={p.id} className="px-3 py-4 font-medium text-foreground">
                        {p.skill_level ? SKILL_LEVEL_LABELS[p.skill_level] ?? "—" : <Unknown />}
                      </td>
                    ))}
                  </CompareRow>
                  <CompareRow label="タイプ">
                    {products.map((p) => (
                      <td key={p.id} className="px-3 py-4 font-medium text-foreground">
                        {p.performance_type ? PERFORMANCE_TYPE_LABELS[p.performance_type] ?? "—" : <Unknown />}
                      </td>
                    ))}
                  </CompareRow>
                  <CompareRow label="発売・世代">
                    {products.map((p) => (
                      <td key={p.id} className="px-3 py-4 text-foreground/75">
                        {[releaseLabel(p.release_date), p.is_current_generation === true ? "現行" : p.is_current_generation === false ? "型落ち" : null]
                          .filter(Boolean)
                          .join("・") || <Unknown />}
                      </td>
                    ))}
                  </CompareRow>
                  {specKeys.map(({ key, label }) => (
                    <CompareRow key={key} label={label}>
                      {products.map((p) => (
                        <td key={p.id} className="px-3 py-4 text-foreground/75">
                          {p.specs?.[key] ?? <Unknown />}
                        </td>
                      ))}
                    </CompareRow>
                  ))}

                  <CompareRow label="現在価格">
                    {products.map((p) => (
                      <td key={p.id} className="px-3 py-4 font-num text-lg font-semibold text-foreground">
                        {yen(p.current_price)}
                      </td>
                    ))}
                  </CompareRow>

                  <CompareRow label="30日平均">
                    {products.map((p) => {
                      const reliable = p.buy_score !== "insufficient_data" && p.history_span_days >= THIN_DATA_DAYS;
                      return (
                        <td key={p.id} className="px-3 py-4 text-foreground/70">
                          {reliable
                            ? yen(p.average_price)
                            : p.history_span_days > 0
                              ? "分析準備中"
                              : "登録されたばかり"}
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

                  <CompareRow label="予測価格">
                    {products.map((p) => (
                      <td key={p.id} className="px-3 py-4 text-accent-dark">
                        {p.forecast_low_price !== null && p.forecast_high_price !== null
                          ? `${yen(p.forecast_low_price)}〜${yen(p.forecast_high_price)}`
                          : "予測情報なし"}
                      </td>
                    ))}
                  </CompareRow>

                  <CompareRow label="予測時期">
                    {products.map((p) => (
                      <td key={p.id} className="px-3 py-4 text-foreground/70">
                        {p.forecast_target_date ? forecastMonthLabel(p.forecast_target_date) : "-"}
                      </td>
                    ))}
                  </CompareRow>

                  <CompareRow label="" last>
                    {products.map((p) => (
                      <td key={p.id} className="px-3 py-6 align-top">
                        <div className="flex flex-col gap-2">
                          {p.affiliate_url ? (
                            <TrackedCta
                              href={p.affiliate_url}
                              target="_blank"
                              rel="noopener noreferrer sponsored"
                              className="block w-full rounded-full bg-brand px-4 py-3 text-center text-xs font-semibold text-on-brand transition-transform hover:scale-[1.03]"
                              event="cta_click"
                              params={{ product_id: p.id, product_slug: p.slug, cta_type: "affiliate_compare" }}
                              productId={p.id}
                              category={p.category}
                              placement={placement}
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
                          {/* Amazon: 実績作りフェーズにつき価格は取得せず、商品名の検索結果への
                              リンクのみ（見た目でRakuten/Yahooの直リンクと混同しないよう別配色）。 */}
                          <TrackedCta
                            href={getAmazonSearchUrl(p.name)}
                            target="_blank"
                            rel="noopener noreferrer sponsored"
                            className="block w-full rounded-full border border-border px-4 py-2.5 text-center text-xs font-semibold text-foreground/60 hover:border-brand/40 hover:text-brand"
                            event="cta_click"
                            params={{ product_id: p.id, product_slug: p.slug, cta_type: "affiliate_search" }}
                            productId={p.id}
                            category={p.category}
                            placement={placement}
                          >
                            Amazonで探す ↗
                          </TrackedCta>
                        </div>
                      </td>
                    ))}
                  </CompareRow>
                </tbody>
              </table>
              <p className="mt-4 text-xs text-foreground/35">
                ※「対象レベル」「タイプ」はメーカー公表の位置づけ、スペックは楽天市場の販売ページ記載の値です（選べるロフト・シャフトは販売ページでご確認ください）。「—」は未確認の項目です。
              </p>
              <p className="mt-1 text-xs text-foreground/35">
                ※「予測価格」「予測時期」の項目は過去の価格データをもとにした予測であり、将来価格を保証するものではありません。
              </p>
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


function Unknown() {
  return <span className="text-foreground/30">—</span>;
}

function releaseLabel(iso: string | null): string | null {
  if (!iso) return null;
  const [y, m] = iso.split("-").map(Number);
  return y && m ? `${y}年${m}月発売` : null;
}
