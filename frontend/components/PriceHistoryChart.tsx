import { PriceHistoryItem } from "@/lib/api";

export default function PriceHistoryChart({ history }: { history: PriceHistoryItem[] }) {
  if (history.length < 2) {
    return <p className="text-sm text-foreground/50">価格履歴がまだ十分に蓄積されていません。</p>;
  }

  const width = 600;
  const height = 160;
  const padding = 24;
  const prices = history.map((h) => h.price);
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const range = max - min || 1;

  const points = history.map((h, i) => {
    const x = padding + (i / (history.length - 1)) * (width - padding * 2);
    const y = height - padding - ((h.price - min) / range) * (height - padding * 2);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });

  return (
    <div className="w-full overflow-x-auto">
      <svg viewBox={`0 0 ${width} ${height}`} className="h-40 w-full min-w-[400px]">
        <polyline
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          className="text-accent"
          points={points.join(" ")}
        />
        {history.map((h, i) => {
          const [x, y] = points[i].split(",");
          return <circle key={h.id} cx={x} cy={y} r={2.5} className="fill-accent-dark" />;
        })}
      </svg>
      <div className="flex justify-between text-xs text-foreground/50">
        <span>{new Date(history[0].recorded_at).toLocaleDateString("ja-JP")}</span>
        <span>
          最安 ¥{min.toLocaleString("ja-JP")} / 最高 ¥{max.toLocaleString("ja-JP")}
        </span>
        <span>{new Date(history[history.length - 1].recorded_at).toLocaleDateString("ja-JP")}</span>
      </div>
    </div>
  );
}
