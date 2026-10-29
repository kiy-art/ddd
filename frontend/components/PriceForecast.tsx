import Link from "next/link";

import { Product } from "@/lib/api";
import { forecastMonthLabel } from "@/lib/forecast";

const CONFIDENCE_META: Record<string, { dotClass: string; label: string }> = {
  high: { dotClass: "bg-signal-high", label: "高" },
  medium: { dotClass: "bg-signal-mid", label: "中" },
  low: { dotClass: "bg-signal-low", label: "低" },
};

const CONFIDENCE_LEVEL: Record<string, number> = { high: 3, medium: 2, low: 1 };

// An icon per kind of reason, picked from words the backend text uses.
function reasonIcon(reason: string): string {
  if (/逆方向|不確実|ばらつき/.test(reason)) return "⚠️";
  if (/傾向|変化|下落|上昇/.test(reason)) return "📉";
  if (/データ|件/.test(reason)) return "📊";
  return "•";
}

function ForecastRangeChart({
  current,
  low,
  high,
  center,
  month,
}: {
  current: number | null;
  low: number;
  high: number;
  center: number;
  month: string;
}) {
  const values = [low, high, center, ...(current !== null ? [current] : [])];
  const min = Math.min(...values);
  const max = Math.max(...values);
  const pad = (max - min) * 0.08 || max * 0.05;
  const pos = (v: number) => ((v - (min - pad)) / (max - min + pad * 2)) * 100;

  return (
    <div
      className="rounded-xl border border-border bg-background px-4 pb-4 pt-9"
      role="img"
      aria-label={`現在${yen(current)}、${month}の予測${yen(low)}〜${yen(high)}（中心${yen(center)}）`}
    >
      <div className="relative h-3 rounded-full bg-foreground/5">
        <div
          className="absolute inset-y-0 rounded-full bg-brand/30"
          style={{ left: `${pos(low)}%`, width: `${pos(high) - pos(low)}%` }}
        />
        <span
          className="absolute top-1/2 h-5 w-1 -translate-x-1/2 -translate-y-1/2 rounded bg-brand"
          style={{ left: `${pos(center)}%` }}
        />
        <span
          className="absolute -top-7 -translate-x-1/2 whitespace-nowrap rounded bg-brand px-1.5 py-0.5 text-[10px] font-semibold text-white"
          style={{ left: `${Math.min(88, Math.max(12, pos(center)))}%` }}
        >
          🔮 {month} {yen(center)}
        </span>
        {current !== null && (
          <>
            <span
              className="absolute top-1/2 h-5 w-5 -translate-x-1/2 -translate-y-1/2 rounded-full border-[3px] border-white bg-foreground shadow"
              style={{ left: `${pos(current)}%` }}
            />
            <span
              className="absolute top-5 -translate-x-1/2 whitespace-nowrap text-[10px] font-semibold text-foreground"
              style={{ left: `${Math.min(88, Math.max(12, pos(current)))}%` }}
            >
              今 {yen(current)}
            </span>
          </>
        )}
      </div>
      <div className="mt-8 flex justify-between font-num text-[10px] text-foreground/45">
        <span>予測下限 {yen(low)}</span>
        <span>予測上限 {yen(high)}</span>
      </div>
    </div>
  );
}

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
        🔮 ここからは予測です（過去の価格からの推測で、将来価格の保証ではありません）
      </p>

      {/* 2026-10-30 (社長指示「グラフ化」): the three number columns became
          one price axis - today's price vs the forecast range. */}
      <ForecastRangeChart
        current={current}
        low={forecastLow}
        high={forecastHigh}
        center={forecastCenter}
        month={forecastMonthLabel(product.forecast_target_date!)}
      />
      <div className="flex flex-wrap gap-2 text-xs">
        <span className="rounded-full bg-foreground/5 px-3 py-1.5 font-medium text-foreground/70">
          {product.forecast_trend === "down" ? "📉" : product.forecast_trend === "up" ? "📈" : "➡️"} {trendLabel}
        </span>
        <span className="inline-flex items-center gap-1.5 rounded-full bg-foreground/5 px-3 py-1.5 font-medium text-foreground/70">
          予測の確度
          <span className="inline-flex gap-0.5" aria-label={confidence.label}>
            {[0, 1, 2].map((k) => (
              <span
                key={k}
                className={`h-2.5 w-2.5 rounded-full ${k < CONFIDENCE_LEVEL[product.forecast_confidence!] ? confidence.dotClass : "bg-foreground/15"}`}
              />
            ))}
          </span>
          {confidence.label}
        </span>
      </div>

      {reasons.length > 0 && (
        <div>
          <span className="text-xs font-medium uppercase tracking-widest text-foreground/40">予測の根拠</span>
          <ul className="mt-2 flex flex-col gap-2">
            {reasons.map((reason, i) => (
              <li key={i} className="flex items-start gap-2.5 rounded-lg bg-background px-3 py-2 text-xs leading-relaxed text-foreground/65">
                <span aria-hidden="true" className="shrink-0 text-base leading-none">{reasonIcon(reason)}</span>
                <span>{reason}</span>
              </li>
            ))}
          </ul>
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
              <ul className="mt-2 flex flex-wrap gap-1.5 text-[11px] font-medium text-foreground/70">
                {["⛳ すぐ使える", "🎯 希望スペックを確保", "🛒 在庫あり"].map((t) => (
                  <li key={t} className="rounded-full bg-brand/10 px-2.5 py-1">{t}</li>
                ))}
              </ul>
            </div>
            <div className="rounded-lg border border-accent/30 bg-accent/5 p-4">
              <span className="text-xs font-semibold text-foreground/50">価格低下を待つ場合</span>
              <p className="mt-1 font-num text-xl font-semibold text-foreground">
                {yen(forecastLow)}〜{yen(forecastHigh)}
              </p>
              <ul className="mt-2 flex flex-wrap gap-1.5 text-[11px] font-medium text-foreground/70">
                {["⚠️ 下がる保証なし", "📦 在庫切れの可能性", "⏳ その間プレーできない"].map((t) => (
                  <li key={t} className="rounded-full bg-foreground/5 px-2.5 py-1">{t}</li>
                ))}
              </ul>
            </div>
          </div>
          {waitMessage && !diffCallout && <p className="mt-3 text-sm leading-relaxed text-foreground/60">{waitMessage}</p>}
          <p className="mt-3 text-[11px] text-foreground/40">※判断材料の提示で、「待つべき」と断定するものではありません。</p>
        </div>
      )}

      <details className="rounded-xl border border-border bg-background px-4 py-3 text-xs leading-relaxed text-foreground/50">
        <summary className="cursor-pointer font-medium text-foreground/60">ℹ️ この価格予測について（タップで開く）</summary>
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
      </details>
    </div>
  );
}
