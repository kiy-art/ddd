import Link from "next/link";

import { Product } from "@/lib/api";
import { forecastMonthLabel } from "@/lib/forecast";

const CONFIDENCE_META: Record<string, { dotClass: string; label: string }> = {
  high: { dotClass: "bg-signal-high", label: "高" },
  medium: { dotClass: "bg-signal-mid", label: "中" },
  low: { dotClass: "bg-signal-low", label: "低" },
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

export default function PriceForecast({ product }: { product: Product }) {
  const hasForecast =
    product.forecast_confidence !== null &&
    product.forecast_center_price !== null &&
    product.forecast_low_price !== null &&
    product.forecast_high_price !== null &&
    product.forecast_target_date !== null;

  return (
    <div>
      <div className="flex items-center gap-2">
        <span className="text-xs font-medium uppercase tracking-[0.3em] text-accent">Price Forecast</span>
        <span className="text-[10px] font-bold uppercase tracking-widest text-accent-dark">予測</span>
      </div>
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
  let diffCallout: { amount: number; percent: number; direction: "down" | "up" } | null = null;
  if (current !== null) {
    if (product.forecast_trend === "down") {
      const min = Math.max(0, current - forecastHigh);
      const max = Math.max(0, current - forecastLow);
      waitMessage = `待った場合、約${yen(min)}〜${yen(max)}安くなる可能性があります。`;
      const amount = current - forecastCenter;
      if (amount > 0) {
        diffCallout = { amount, percent: Math.round((amount / current) * 100), direction: "down" };
      }
    } else if (product.forecast_trend === "up") {
      const min = Math.max(0, forecastLow - current);
      const max = Math.max(0, forecastHigh - current);
      waitMessage = `待つと約${yen(min)}〜${yen(max)}高くなる可能性があります。今のうちの購入も選択肢です。`;
      const amount = forecastCenter - current;
      if (amount > 0) {
        diffCallout = { amount, percent: Math.round((amount / current) * 100), direction: "up" };
      }
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
          <p className="mt-1 font-num text-2xl font-semibold text-foreground">{yen(forecastCenter)}</p>
          <p className="mt-0.5 text-xs text-foreground/45">
            予測レンジ {yen(forecastLow)}〜{yen(forecastHigh)}
          </p>
        </div>
        <div>
          <span className="text-xs text-foreground/45">予測時期</span>
          <p className="mt-1 font-display text-2xl font-semibold text-foreground">
            {forecastMonthLabel(product.forecast_target_date!)}
          </p>
          <p className="mt-0.5 text-xs text-foreground/45">{trendLabel}</p>
        </div>
        <div>
          <span className="text-xs text-foreground/45">予測信頼度</span>
          <p className="mt-1 flex items-center gap-2 font-display text-2xl font-semibold text-foreground">
            <span className={`inline-block h-2.5 w-2.5 rounded-full ${confidence.dotClass}`} aria-hidden />
            {confidence.label}
          </p>
          <p className="mt-0.5 text-xs text-foreground/45">利用できる価格データの量に基づく確度です</p>
        </div>
      </div>

      {reasons.length > 0 && (
        <div>
          <span className="text-xs font-medium uppercase tracking-widest text-foreground/40">予測の根拠</span>
          <ol className="mt-2 flex flex-col gap-2 text-sm text-foreground/60">
            {reasons.map((reason, i) => (
              <li key={i} className="flex gap-2.5">
                <span className="shrink-0 font-display text-xs font-semibold text-accent-dark">
                  {["①", "②", "③", "④", "⑤"][i] ?? `${i + 1}.`}
                </span>
                <span>{reason}</span>
              </li>
            ))}
          </ol>
        </div>
      )}

      {current !== null && (
        <div className="rounded-xl border border-border bg-background p-5">
          <span className="text-xs font-medium uppercase tracking-widest text-foreground/40">今買う vs 待つ</span>

          {diffCallout && (
            <div className="mt-3 flex items-baseline gap-3 rounded-lg bg-card px-4 py-3">
              <span className="text-xs text-foreground/45">予測される差額</span>
              <span className="font-num text-2xl font-semibold text-foreground">{yen(diffCallout.amount)}</span>
              <span className={`text-sm font-semibold ${diffCallout.direction === "down" ? "text-brand dark:text-brand-light" : "text-foreground/60"}`}>
                約{diffCallout.percent}%{diffCallout.direction === "down" ? "安くなる" : "高くなる"}可能性
              </span>
            </div>
          )}

          <div className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="rounded-lg border border-border bg-card p-4">
              <span className="text-xs font-semibold text-foreground/50">今購入する場合</span>
              <p className="mt-1 font-num text-xl font-semibold text-foreground">{yen(current)}</p>
              <ul className="mt-2 flex flex-col gap-1 text-xs text-foreground/55">
                <li>・在庫があり、すぐに購入できる</li>
                <li>・希望のスペック（色・サイズ等）を確保しやすい</li>
                <li>・価格が下がる保証を待つ必要がない</li>
              </ul>
            </div>
            <div className="rounded-lg border border-accent/30 bg-accent/5 p-4">
              <span className="text-xs font-semibold text-foreground/50">価格低下を待つ場合</span>
              <p className="mt-1 font-num text-xl font-semibold text-foreground">
                {yen(forecastLow)}〜{yen(forecastHigh)}
              </p>
              <ul className="mt-2 flex flex-col gap-1 text-xs text-foreground/55">
                <li>・価格が下がる保証はない（あくまで予測）</li>
                <li>・在庫切れ・希望スペック終売の可能性がある</li>
                <li>・待っている間はプレーに使えない</li>
              </ul>
            </div>
          </div>
          {waitMessage && <p className="mt-3 text-sm leading-relaxed text-foreground/60">{waitMessage}</p>}
          <p className="mt-3 text-xs text-foreground/40">
            ※これは判断材料の提示であり、「待つべき」と断定するものではありません。在庫状況やモデルチェンジ等により実際の価格は変動します。
          </p>
        </div>
      )}

      <div className="rounded-xl border border-border bg-background px-4 py-4 text-xs leading-relaxed text-foreground/50">
        <p className="font-medium text-foreground/60">この価格予測について</p>
        <ul className="mt-2 flex flex-col gap-1">
          <li>・この商品自身の過去の価格データ（実績）のみを基にした機械的な傾向分析であり、AIが自由に判断したものではありません。</li>
          <li>・将来価格を保証するものではありません。</li>
          <li>・市場状況によって実際の価格は大きく変動する可能性があります。</li>
          <li>・後継モデルの発売時期など、メーカーの発売予定が変更される可能性があります。</li>
          <li>・在庫状況によって価格が変わる場合があります。</li>
          <li>・モデルチェンジ周期や季節ごとの傾向は、商品固有のデータとしては十分に蓄積され次第、分析に加える予定です（現時点では商品固有の予測には未使用）。</li>
          <li>・公式のメーカー発表に基づく情報ではありません。</li>
        </ul>
        <Link href="/guides/how-to-read-price-forecast" className="mt-2 inline-block font-medium text-brand hover:underline">
          価格予測の詳しい見方はこちら →
        </Link>
      </div>
    </div>
  );
}
