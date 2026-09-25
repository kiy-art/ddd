// A compact version of PriceRangeBar for use inside a product card grid,
// where full labels don't fit. Answers the one question a raw price number
// can't: is today's price near this product's own low, or near its high?
// Only ever called with real recorded values (lowest_price/average_price
// from the API) - never a fabricated range.
export default function MiniPriceRangeBar({
  low,
  average,
  current,
}: {
  low: number;
  average: number;
  current: number;
}) {
  const min = Math.min(low, average, current);
  const max = Math.max(low, average, current);
  const span = max - min || 1;
  const pos = (v: number) => ((v - min) / span) * 100;

  return (
    <div className="flex flex-col gap-1">
      <div className="relative h-1.5 rounded-full bg-background">
        <div
          className="absolute top-1/2 h-1 w-1 -translate-x-1/2 -translate-y-1/2 rounded-full bg-foreground/25"
          style={{ left: `${pos(average)}%` }}
        />
        <div
          className="absolute top-1/2 h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-card bg-brand shadow-sm"
          style={{ left: `${pos(current)}%` }}
        />
      </div>
      <div className="flex justify-between text-[9px] uppercase tracking-widest text-foreground/35">
        <span>最安</span>
        <span>平均</span>
      </div>
    </div>
  );
}
