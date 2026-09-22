function yen(value: number): string {
  return `¥${value.toLocaleString("ja-JP")}`;
}

function pct(from: number, to: number): number {
  return Math.round(((to - from) / from) * 1000) / 10;
}

function pctLabel(value: number): string {
  return `${value > 0 ? "+" : ""}${value}%`;
}

interface Marker {
  name: string;
  pos: number;
  value: number;
  emphasis?: boolean;
}

// Below this many percentage points apart on the bar, two labels would
// visually overlap - merge them into one instead of letting one silently
// hide the other. This is common and not an edge case: the current price
// being exactly at (or very near) the all-time low or the 30-day average
// happens often.
const LABEL_COLLISION_THRESHOLD = 12;

function mergeMarkers(markers: Marker[]): { names: string[]; pos: number; values: number[]; emphasis: boolean }[] {
  const sorted = [...markers].sort((a, b) => a.pos - b.pos);
  const groups: { names: string[]; pos: number; values: number[]; emphasis: boolean }[] = [];
  for (const m of sorted) {
    const last = groups[groups.length - 1];
    if (last && m.pos - last.pos < LABEL_COLLISION_THRESHOLD) {
      last.names.push(m.name);
      if (!last.values.includes(m.value)) last.values.push(m.value);
      last.pos = m.emphasis ? m.pos : last.pos; // prefer the "current" marker's exact position
      last.emphasis = last.emphasis || !!m.emphasis;
    } else {
      groups.push({ names: [m.name], pos: m.pos, values: [m.value], emphasis: !!m.emphasis });
    }
  }
  return groups;
}

function PriceRangeLabels({ markers }: { markers: Marker[] }) {
  const groups = mergeMarkers(markers);
  return (
    <div className="relative mt-2 h-8 text-[11px] text-foreground/45">
      {groups.map((g) => (
        <span
          key={g.names.join("/")}
          className={`absolute -translate-x-1/2 text-center ${
            g.emphasis ? "font-semibold text-brand dark:text-brand-light" : ""
          }`}
          style={{ left: `${g.pos}%` }}
        >
          {g.names.join("/")}
          <br />
          {g.values.map((v) => yen(v)).join(" ・ ")}
        </span>
      ))}
    </div>
  );
}

/**
 * Where the current price sits between this product's own recorded low,
 * average and high - all three read straight from real data (lowest_price/
 * average_price from the API, highest computed client-side from the same
 * price_history array already on the page - see product/[slug]/page.tsx).
 * No product ever gets a fabricated range: callers only render this once
 * low/avg/high/current are all non-null.
 */
export default function PriceRangeBar({
  low,
  average,
  high,
  current,
}: {
  low: number;
  average: number;
  high: number;
  current: number;
}) {
  const min = Math.min(low, current);
  const max = Math.max(high, current);
  const span = max - min || 1;
  const posOf = (v: number) => ((v - min) / span) * 100;

  return (
    <div className="rounded-2xl border border-border bg-card p-6">
      <span className="text-xs font-medium uppercase tracking-widest text-foreground/40">価格帯における現在地</span>

      <div className="relative mt-8 h-2 rounded-full bg-background">
        <div
          className="absolute h-2 rounded-full bg-border"
          style={{ left: `${posOf(low)}%`, width: `${posOf(high) - posOf(low)}%` }}
        />
        {/* average marker */}
        <div
          className="absolute top-1/2 h-3 w-0.5 -translate-y-1/2 bg-foreground/40"
          style={{ left: `${posOf(average)}%` }}
        />
        {/* current price marker */}
        <div
          className="absolute top-1/2 h-4 w-4 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-card bg-brand shadow-sm"
          style={{ left: `${posOf(current)}%` }}
        />
      </div>

      <PriceRangeLabels
        markers={[
          { name: "最安", pos: posOf(low), value: low },
          { name: "平均", pos: posOf(average), value: average },
          { name: "現在", pos: posOf(current), value: current, emphasis: true },
        ]}
      />


      <div className="mt-6 grid grid-cols-3 gap-3 border-t border-border pt-4 text-center">
        <div>
          <dt className="text-[11px] text-foreground/45">過去最安比</dt>
          <dd
            className={`mt-1 font-display text-lg font-semibold ${
              pct(low, current) > 0 ? "text-foreground" : "text-brand dark:text-brand-light"
            }`}
          >
            {pctLabel(pct(low, current))}
          </dd>
        </div>
        <div>
          <dt className="text-[11px] text-foreground/45">過去平均比</dt>
          <dd
            className={`mt-1 font-display text-lg font-semibold ${
              pct(average, current) > 0 ? "text-foreground" : "text-brand dark:text-brand-light"
            }`}
          >
            {pctLabel(pct(average, current))}
          </dd>
        </div>
        <div>
          <dt className="text-[11px] text-foreground/45">過去最高値比</dt>
          <dd className="mt-1 font-display text-lg font-semibold text-foreground">{pctLabel(pct(high, current))}</dd>
        </div>
      </div>
    </div>
  );
}
