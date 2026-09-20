import { PriceHistoryItem } from "@/lib/api";
import { smoothPath } from "@/lib/chart";

function monthKey(dateStr: string): string {
  const d = new Date(dateStr);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

function monthLabel(key: string): string {
  const [y, m] = key.split("-");
  return `${y}/${m}`;
}

export default function MonthlyTrendChart({ history }: { history: PriceHistoryItem[] }) {
  const buckets = new Map<string, number[]>();
  for (const h of history) {
    const key = monthKey(h.recorded_at);
    if (!buckets.has(key)) buckets.set(key, []);
    buckets.get(key)!.push(h.price);
  }

  const months = Array.from(buckets.keys()).sort();
  const monthlyAverages = months.map((key) => {
    const prices = buckets.get(key)!;
    return { key, avg: Math.round(prices.reduce((s, p) => s + p, 0) / prices.length) };
  });

  if (monthlyAverages.length < 2) {
    return (
      <div className="rounded-xl border border-dashed border-border bg-background px-4 py-10 text-center text-sm text-foreground/45">
        <p>長期の月次推移データを蓄積中です。</p>
        <p className="mt-1 text-xs text-foreground/35">
          毎日の自動更新が有効になると、月ごとの平均価格としてここに表示されていきます（最大3年分）。
        </p>
      </div>
    );
  }

  const width = 640;
  const height = 200;
  const padTop = 24;
  const padBottom = 32;
  const padX = 8;

  const values = monthlyAverages.map((m) => m.avg);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;

  const points = monthlyAverages.map((m, i) => ({
    x: padX + (i / (monthlyAverages.length - 1)) * (width - padX * 2),
    y: padTop + (1 - (m.avg - min) / range) * (height - padTop - padBottom),
  }));

  const linePath = smoothPath(points);
  const step = Math.max(1, Math.ceil(monthlyAverages.length / 8));

  return (
    <div className="w-full">
      <div className="w-full overflow-x-auto">
        <svg viewBox={`0 0 ${width} ${height}`} className="h-48 w-full min-w-[420px]">
          {[0.25, 0.5, 0.75].map((f) => (
            <line
              key={f}
              x1={padX}
              x2={width - padX}
              y1={padTop + f * (height - padTop - padBottom)}
              y2={padTop + f * (height - padTop - padBottom)}
              stroke="var(--border)"
              strokeWidth={1}
            />
          ))}
          <path
            d={linePath}
            fill="none"
            stroke="var(--accent)"
            strokeWidth={2.5}
            strokeLinecap="round"
            pathLength={1}
            className="animate-draw"
          />
          {points.map((p, i) => (
            <circle key={monthlyAverages[i].key} cx={p.x} cy={p.y} r={3} fill="var(--accent-dark)" />
          ))}
        </svg>
      </div>
      <div className="mt-2 flex justify-between text-[10px] text-foreground/40">
        {monthlyAverages
          .filter((_, i) => i % step === 0 || i === monthlyAverages.length - 1)
          .map((m) => (
            <span key={m.key}>{monthLabel(m.key)}</span>
          ))}
      </div>
      <p className="mt-3 text-xs text-foreground/45">
        月平均 最安 ¥{min.toLocaleString("ja-JP")} ・ 最高 ¥{max.toLocaleString("ja-JP")}
        {monthlyAverages.length < 36 && "（データ蓄積中。毎日の自動更新で最大3年分まで表示されます）"}
      </p>
    </div>
  );
}
