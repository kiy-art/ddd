import { Product } from "@/lib/api";

const CONFIDENCE_META: Record<string, { dot: string; label: string }> = {
  high: { dot: "🟢", label: "高" },
  medium: { dot: "🟡", label: "中" },
  low: { dot: "⚪", label: "低" },
};

const TREND_LABEL: Record<string, string> = {
  down: "下落傾向",
  up: "上昇傾向",
  flat: "横ばい傾向",
};

function yen(value: number | null): string {
  if (value === null) return "-";
  return `¥${value.toLocaleString("ja-JP")}`;
}

function monthLabel(dateStr: string): string {
  const d = new Date(dateStr);
  return `${d.getFullYear()}年${d.getMonth() + 1}月頃`;
}

export default function PriceForecast({ product }: { product: Product }) {
  const hasForecast =
    product.forecast_confidence !== null &&
    product.forecast_center_price !== null &&
    product.forecast_low_price !== null &&
    product.forecast_high_price !== null &&
    product.forecast_target_date !== null;

  return (
    <div className="rounded-2xl border border-border bg-card p-6 sm:p-10">
      <span className="text-xs font-medium uppercase tracking-[0.3em] text-accent">🔮 Price Forecast</span>
      <h2 className="mt-2 font-display text-2xl font-semibold text-foreground">価格予測</h2>

      {!hasForecast ? (
        <p className="mt-4 text-sm leading-relaxed text-foreground/50">
          価格履歴が不足しているため、価格予測は現在ご利用いただけません。価格データが十分に蓄積され次第、表示されます。
        </p>
      ) : (
        <ForecastBody product={product} />
      )}
    </div>
  );
}

function ForecastBody({ product }: { product: Product }) {
  const confidence = CONFIDENCE_META[product.forecast_confidence!] ?? CONFIDENCE_META.low;
  const trendLabel = TREND_LABEL[product.forecast_trend ?? "flat"];
  const reasons = (product.forecast_reason ?? "").split("\n").filter(Boolean);

  const current = product.current_price;
  const forecastLow = product.forecast_low_price!;
  const forecastHigh = product.forecast_high_price!;
  const forecastCenter = product.forecast_center_price!;

  let waitMessage: string | null = null;
  if (current !== null) {
    if (product.forecast_trend === "down") {
      const min = Math.max(0, current - forecastHigh);
      const max = Math.max(0, current - forecastLow);
      waitMessage = `待った場合、約${yen(min)}〜${yen(max)}安くなる可能性があります。`;
    } else if (product.forecast_trend === "up") {
      const min = Math.max(0, forecastLow - current);
      const max = Math.max(0, forecastHigh - current);
      waitMessage = `待つと約${yen(min)}〜${yen(max)}高くなる可能性があります。今のうちの購入も選択肢です。`;
    } else {
      waitMessage = "大きな価格変動は予測されていません。";
    }
  }

  return (
    <div className="mt-5 flex flex-col gap-6">
      <p className="rounded-lg bg-background px-3 py-2 text-xs font-medium text-foreground/50">
        ここからは予測です。過去の価格データをもとにした推測であり、将来価格を保証するものではありません。
      </p>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div>
          <span className="text-xs text-foreground/45">予測中心値</span>
          <p className="mt-1 font-display text-2xl font-semibold text-foreground">{yen(forecastCenter)}</p>
          <p className="mt-0.5 text-xs text-foreground/45">
            予測レンジ {yen(forecastLow)}〜{yen(forecastHigh)}
          </p>
        </div>
        <div>
          <span className="text-xs text-foreground/45">予測時期</span>
          <p className="mt-1 font-display text-2xl font-semibold text-foreground">
            {monthLabel(product.forecast_target_date!)}
          </p>
          <p className="mt-0.5 text-xs text-foreground/45">{trendLabel}</p>
        </div>
        <div>
          <span className="text-xs text-foreground/45">予測信頼度</span>
          <p className="mt-1 font-display text-2xl font-semibold text-foreground">
            {confidence.dot} {confidence.label}
          </p>
          <p className="mt-0.5 text-xs text-foreground/45">利用できる価格データの量に基づく確度です</p>
        </div>
      </div>

      {reasons.length > 0 && (
        <div>
          <span className="text-xs font-medium uppercase tracking-widest text-foreground/40">予測の根拠</span>
          <ul className="mt-2 flex flex-col gap-1.5 text-sm text-foreground/60">
            {reasons.map((reason, i) => (
              <li key={i} className="flex gap-2">
                <span className="text-foreground/30">・</span>
                <span>{reason}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {current !== null && (
        <div className="rounded-xl border border-border bg-background p-5">
          <span className="text-xs font-medium uppercase tracking-widest text-foreground/40">
            今買う / 待つ
          </span>
          <div className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <span className="text-xs text-foreground/45">今買う場合</span>
              <p className="mt-1 font-display text-xl font-semibold text-foreground">現在価格 {yen(current)}</p>
            </div>
            <div>
              <span className="text-xs text-foreground/45">待つ場合の予測</span>
              <p className="mt-1 font-display text-xl font-semibold text-foreground">
                {yen(forecastLow)}〜{yen(forecastHigh)}
              </p>
            </div>
          </div>
          {waitMessage && <p className="mt-3 text-sm leading-relaxed text-foreground/60">{waitMessage}</p>}
          <p className="mt-3 text-xs text-foreground/40">
            ※これは判断材料の提示であり、「待つべき」と断定するものではありません。在庫状況やモデルチェンジ等により実際の価格は変動します。
          </p>
        </div>
      )}

      <details className="rounded-xl border border-border bg-background px-4 py-3 text-xs leading-relaxed text-foreground/50">
        <summary className="cursor-pointer font-medium text-foreground/60">この予測について</summary>
        <ul className="mt-2 flex flex-col gap-1">
          <li>・この商品の過去の価格データ（実績）のみを基にした傾向分析です。</li>
          <li>・モデルチェンジ時期や季節ごとの傾向は、十分なデータが蓄積され次第、分析に加える予定です（現時点では未使用）。</li>
          <li>・将来の価格を保証するものではなく、実際の価格は在庫状況や市場動向により変動します。</li>
          <li>・公式のメーカー発表に基づく情報ではありません。</li>
        </ul>
      </details>
    </div>
  );
}
