import { PriceHistoryItem } from "@/lib/api";
import { smoothPath } from "@/lib/chart";

export interface ChartForecast {
  centerPrice: number;
  lowPrice: number;
  highPrice: number;
  targetDate: string;
}

export default function PriceHistoryChart({
  history,
  forecast,
}: {
  history: PriceHistoryItem[];
  forecast?: ChartForecast | null;
}) {
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

  const firstTime = new Date(history[0].recorded_at).getTime();
  const lastTime = new Date(history[history.length - 1].recorded_at).getTime();
  const forecastTime = forecast ? new Date(forecast.targetDate).getTime() : lastTime;
  const totalTime = Math.max(forecastTime - firstTime, 1);
  const xAt = (t: number) => padX + ((t - firstTime) / totalTime) * (width - padX * 2);

  const prices = history.map((h) => h.price);
  const rangeValues = forecast ? [...prices, forecast.lowPrice, forecast.highPrice] : prices;
  const min = Math.min(...rangeValues);
  const max = Math.max(...rangeValues);
  const range = max - min || 1;
  const yAt = (p: number) => padTop + (1 - (p - min) / range) * (height - padTop - padBottom);

  const points = history.map((h) => ({ x: xAt(new Date(h.recorded_at).getTime()), y: yAt(h.price) }));

  const linePath = smoothPath(points);
  const areaPath = `${linePath} L ${points[points.length - 1].x} ${height - padBottom} L ${points[0].x} ${height - padBottom} Z`;
  const last = points[points.length - 1];
  const lastPrice = history[history.length - 1].price;

  const forecastX = forecast ? xAt(forecastTime) : null;
  const forecastCenterY = forecast ? yAt(forecast.centerPrice) : null;
  const forecastLowY = forecast ? yAt(forecast.lowPrice) : null;
  const forecastHighY = forecast ? yAt(forecast.highPrice) : null;
  const conePath =
    forecast && forecastX !== null && forecastLowY !== null && forecastHighY !== null
      ? `M ${last.x} ${last.y} L ${forecastX} ${forecastLowY} L ${forecastX} ${forecastHighY} Z`
      : null;

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
              x2={forecastX ?? width - padX}
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

          {conePath && (
            <>
              {/* Uncertainty cone: widens toward the forecast target, kept
                  visually light so it reads as "estimated range", not fact. */}
              <path d={conePath} fill="var(--accent)" fillOpacity={0.12} stroke="none" />
              <line
                x1={last.x}
                y1={last.y}
                x2={forecastX!}
                y2={forecastCenterY!}
                stroke="var(--accent-dark)"
                strokeWidth={2}
                strokeDasharray="5 4"
                strokeLinecap="round"
              />
              <line
                x1={last.x}
                y1={padTop}
                x2={last.x}
                y2={height - padBottom}
                stroke="var(--border)"
                strokeWidth={1}
                strokeDasharray="3 3"
              />
              <circle cx={forecastX!} cy={forecastCenterY!} r={4} fill="var(--card)" stroke="var(--accent-dark)" strokeWidth={2} />
              <text x={padX} y={16} fontSize={10} fontWeight={600} letterSpacing="0.08em" fill="var(--foreground)" opacity={0.4}>
                実績
              </text>
              <text
                x={Math.min(forecastX! - 4, width - 30)}
                y={16}
                textAnchor="end"
                fontSize={10}
                fontWeight={600}
                letterSpacing="0.08em"
                fill="var(--accent-dark)"
              >
                予測
              </text>
            </>
          )}

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
