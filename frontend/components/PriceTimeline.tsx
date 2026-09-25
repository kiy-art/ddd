import SeasonalTrend from "@/components/SeasonalTrend";
import { Product } from "@/lib/api";
import { forecastMonthLabel } from "@/lib/forecast";
import { MODEL_CYCLE_DISCLAIMER, MODEL_CYCLE_FACT_NOTE, getModelCycleInsight } from "@/lib/modelCycle";

function yen(value: number): string {
  return `¥${value.toLocaleString("ja-JP")}`;
}

const TREND_TIMELINE_LABEL: Record<string, string> = {
  down: "値下がりする可能性",
  up: "値上がりする可能性",
  flat: "大きな変動はない見込み",
};

/**
 * "いつ安くなりそうか" - deliberately built from only two real inputs: this
 * product's own forecast (if the backend produced one) and the category's
 * general, non-per-product seasonal pattern text (SeasonalTrend). No
 * star-rated "buy-time calendar" with a score per month, because we have no
 * real per-month statistical backing for that - assigning a precise-looking
 * number to each month would be exactly the fabrication the redesign brief
 * explicitly rules out. This can grow a real calendar once actual event/
 * seasonal statistics are connected (see the DataSource section).
 */
export default function PriceTimeline({ product }: { product: Product }) {
  const hasForecast =
    product.forecast_trend !== null && product.forecast_target_date !== null && product.forecast_low_price !== null && product.forecast_high_price !== null;

  // Only consulted when there's no real per-product forecast yet - a
  // release-date/generation-based read is strictly weaker evidence than an
  // actual price-history trend, so it never overrides one.
  const cycleInsight = hasForecast
    ? null
    : getModelCycleInsight({ release_date: product.release_date, is_current_generation: product.is_current_generation });

  return (
    <div>
      <h3 className="font-display text-lg font-semibold text-foreground">いつ安くなりそう？</h3>

      <div className="mt-5 flex flex-col gap-3">
        <div className="flex items-start gap-3 rounded-xl border border-border bg-background p-4">
          <span className="mt-0.5 shrink-0 text-[10px] font-bold uppercase tracking-widest text-emerald-700 dark:text-emerald-500">
            実績
          </span>
          <div className="text-sm leading-relaxed text-foreground/70">
            現在価格 <span className="font-semibold text-foreground">{yen(product.current_price ?? 0)}</span>
            （最終更新はページ下部の価格比較欄をご確認ください）
          </div>
        </div>

        {hasForecast ? (
          <div className="flex items-start gap-3 rounded-xl border border-accent/30 bg-accent/5 p-4">
            <span className="mt-0.5 shrink-0 text-[10px] font-bold uppercase tracking-widest text-accent-dark">
              予測
            </span>
            <div className="text-sm leading-relaxed text-foreground/70">
              <span className="font-semibold text-foreground">{forecastMonthLabel(product.forecast_target_date!)}</span>
              　頃：{TREND_TIMELINE_LABEL[product.forecast_trend!]}
              {product.forecast_trend !== "flat" && (
                <>
                  （目安 {yen(product.forecast_low_price!)}〜{yen(product.forecast_high_price!)}）
                </>
              )}
              <p className="mt-1 text-xs text-foreground/40">
                ※この商品自身の価格データに基づくAI予測です。将来価格を保証するものではありません。
              </p>
            </div>
          </div>
        ) : cycleInsight ? (
          <div
            className="flex items-start gap-3 rounded-xl border border-dashed p-4"
            style={{ borderColor: cycleInsight.tier === "fact" ? "var(--ink)" : "var(--accent-dark)" }}
          >
            <span
              className="mt-0.5 shrink-0 text-[10px] font-bold uppercase tracking-widest"
              style={{ color: cycleInsight.tier === "fact" ? "var(--ink)" : "var(--accent-dark)" }}
            >
              {cycleInsight.tier === "fact" ? "実績" : "AI推測"}
            </span>
            <div className="text-sm leading-relaxed text-foreground/70">
              <span className="font-semibold text-foreground">{cycleInsight.stageLabel}</span>
              　{cycleInsight.message}
              <p className="mt-1 text-xs text-foreground/40">
                {cycleInsight.tier === "fact" ? MODEL_CYCLE_FACT_NOTE : MODEL_CYCLE_DISCLAIMER}
              </p>
            </div>
          </div>
        ) : (
          <div className="flex items-start gap-3 rounded-xl border border-dashed border-border bg-background p-4">
            <span className="mt-0.5 shrink-0 text-[10px] font-bold uppercase tracking-widest text-foreground/40">
              データ不足
            </span>
            <p className="text-sm leading-relaxed text-foreground/50">
              この商品の価格予測に必要なデータがまだ蓄積されていません。データが増え次第、この商品自身の傾向に基づく予測を表示します。
            </p>
          </div>
        )}
      </div>

      <div className="mt-6 border-t border-border pt-6">
        <SeasonalTrend category={product.category} />
      </div>
    </div>
  );
}
