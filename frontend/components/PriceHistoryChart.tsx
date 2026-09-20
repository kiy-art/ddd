import { PriceHistoryItem } from "@/lib/api";

function smoothPath(points: { x: number; y: number }[]): string {
  if (points.length < 2) return "";
  let d = `M ${points[0].x} ${points[0].y}`;
  for (let i = 0; i < points.length - 1; i++) {
    const p0 = points[i - 1] ?? points[i];
    const p1 = points[i];
    const p2 = points[i + 1];
    const p3 = points[i + 2] ?? p2;
    const c1x = p1.x + (p2.x - p0.x) / 6;
    const c1y = p1.y + (p2.y - p0.y) / 6;
    const c2x = p2.x - (p3.x - p1.x) / 6;
    const c2y = p2.y - (p3.y - p1.y) / 6;
    d += ` C ${c1x} ${c1y}, ${c2x} ${c2y}, ${p2.x} ${p2.y}`;
  }
  return d;
}

export default function PriceHistoryChart({ history }: { history: PriceHistoryItem[] }) {
  if (history.length < 2) {
    return (
      <p className="rounded-xl border border-dashed border-border bg-background px-4 py-10 text-center text-sm text-foreground/45">
        価格履歴がまだ十分に蓄積されていません。
      </p>
    );
  }

  const width = 640;
  const height = 220;
  const padTop = 28;
  const padBottom = 36;
  const padX = 8;

  const prices = history.map((h) => h.price);
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const range = max - min || 1;

  const points = history.map((h, i) => ({
    x: padX + (i / (history.length - 1)) * (width - padX * 2),
    y: padTop + (1 - (h.price - min) / range) * (height - padTop - padBottom),
  }));

  const linePath = smoothPath(points);
  const areaPath = `${linePath} L ${points[points.length - 1].x} ${height - padBottom} L ${points[0].x} ${height - padBottom} Z`;
  const last = points[points.length - 1];
  const lastPrice = history[history.length - 1].price;

  return (
    <div className="w-full">
      <div className="w-full overflow-x-auto">
        <svg viewBox={`0 0 ${width} ${height}`} className="h-56 w-full min-w-[420px]">
          <defs>
            <linearGradient id="price-area" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--brand)" stopOpacity="0.16" />
              <stop offset="100%" stopColor="var(--brand)" stopOpacity="0" />
            </linearGradient>
          </defs>

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

          <path d={areaPath} fill="url(#price-area)" stroke="none" />
          <path
            d={linePath}
            fill="none"
            stroke="var(--brand)"
            strokeWidth={2.5}
            strokeLinecap="round"
            pathLength={1}
            className="animate-draw"
          />

          <circle cx={last.x} cy={last.y} r={4.5} fill="var(--brand)" stroke="var(--card)" strokeWidth={2} />
          <text
            x={Math.min(last.x, width - 90)}
            y={Math.max(last.y - 14, 16)}
            className="font-display"
            fontSize={13}
            fontWeight={600}
            fill="var(--foreground)"
          >
            ¥{lastPrice.toLocaleString("ja-JP")}
          </text>
        </svg>
      </div>
      <div className="mt-3 flex justify-between text-xs text-foreground/45">
        <span>{new Date(history[0].recorded_at).toLocaleDateString("ja-JP")}</span>
        <span>
          最安 ¥{min.toLocaleString("ja-JP")} ・ 最高 ¥{max.toLocaleString("ja-JP")}
        </span>
        <span>{new Date(history[history.length - 1].recorded_at).toLocaleDateString("ja-JP")}</span>
      </div>
    </div>
  );
}
