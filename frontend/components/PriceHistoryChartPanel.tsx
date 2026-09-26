"use client";

import { useMemo, useState } from "react";

import PriceHistoryChart, { ChartForecast, ChartReferenceLine } from "@/components/PriceHistoryChart";
import { PriceHistoryItem } from "@/lib/api";

const PERIODS = [
  { key: "1m", label: "1ヶ月", days: 30 },
  { key: "3m", label: "3ヶ月", days: 90 },
  { key: "6m", label: "6ヶ月", days: 180 },
  { key: "1y", label: "1年", days: 365 },
  { key: "all", label: "全期間", days: null },
] as const;

type PeriodKey = (typeof PERIODS)[number]["key"];

export default function PriceHistoryChartPanel({
  history,
  forecast,
  referenceLines,
}: {
  history: PriceHistoryItem[];
  forecast?: ChartForecast | null;
  referenceLines?: ChartReferenceLine[];
}) {
  const [period, setPeriod] = useState<PeriodKey>("all");

  const filtered = useMemo(() => {
    const days = PERIODS.find((p) => p.key === period)?.days;
    if (!days || history.length === 0) return history;
    const cutoff = new Date(history[history.length - 1].recorded_at).getTime() - days * 86400000;
    return history.filter((h) => new Date(h.recorded_at).getTime() >= cutoff);
  }, [history, period]);

  // A period filter only shows a forecast cone when it actually covers the
  // most recent point - otherwise the cone would appear to float in space
  // disconnected from the visible line.
  const showForecast = period === "all" || period === "1y" || filtered.length === history.length;

  return (
    <div>
      {/* Segmented control (TradingView-style range switcher). */}
      <div className="mb-4 inline-flex flex-wrap gap-0.5 rounded-full border border-border bg-background p-1" role="tablist" aria-label="表示期間">
        {PERIODS.map((p) => (
          <button
            key={p.key}
            role="tab"
            aria-selected={period === p.key}
            onClick={() => setPeriod(p.key)}
            className={`tap rounded-full px-3.5 py-1.5 text-xs font-semibold ${
              period === p.key
                ? "bg-card text-foreground shadow-[0_1px_2px_rgba(6,16,12,0.08),0_0_0_1px_var(--border-strong)]"
                : "text-foreground/50 hover:text-foreground"
            }`}
          >
            {p.label}
          </button>
        ))}
      </div>

      {filtered.length < 2 ? (
        <p className="rounded-xl border border-dashed border-border bg-background px-4 py-10 text-center text-sm text-foreground/45">
          この期間の価格履歴データを収集中です。期間を変更するか、しばらくしてから再度ご確認ください。
        </p>
      ) : (
        <PriceHistoryChart
          history={filtered}
          forecast={showForecast ? forecast : null}
          referenceLines={referenceLines}
        />
      )}
    </div>
  );
}
