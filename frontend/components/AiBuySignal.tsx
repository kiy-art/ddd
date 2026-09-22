import CountUp from "@/components/CountUp";
import { getFallbackValueScore } from "@/lib/fallbackScore";

const SIGNAL_LABELS: Record<string, string> = {
  strong_buy: "STRONG BUY",
  buy: "BUY NOW",
  neutral: "HOLD",
  not_buy: "WAIT",
  // Reached only when there's neither enough price history nor an MSRP to
  // fall back on (see FALLBACK_LABEL below) - the true "nothing to show
  // yet" case. "ANALYZING" used to sit here, but it reads as a stuck
  // process rather than an honest "this is a newly-tracked listing", which
  // is what's actually true.
  insufficient_data: "NEW LISTING",
};

// A separate, deliberately different-sounding label from the real
// SIGNAL_LABELS above - this number is not the same kind of claim (see
// lib/fallbackScore.ts), so it must never look like one.
const FALLBACK_LABEL = "定価比較";

// Below this many days of accumulated price history, a confident score
// would overstate how much is actually known - shown as "still analyzing"
// instead, everywhere this badge appears (matches the product page's and
// ProductCard's own thin-data handling).
const THIN_DATA_DAYS = 7;

function signalColorVar(buyScore: string): string {
  if (buyScore === "strong_buy" || buyScore === "buy") return "var(--signal-high)";
  if (buyScore === "neutral") return "var(--signal-mid)";
  return "var(--signal-low)";
}

const SIZES = {
  sm: { box: 56, ring: 5, scoreText: "text-base", labelText: "text-[9px]" },
  lg: { box: 108, ring: 7, scoreText: "text-3xl", labelText: "text-[11px]" },
} as const;

export default function AiBuySignal({
  buyScore,
  buySignalScore,
  historySpanDays,
  msrp = null,
  currentPrice = null,
  releaseDate = null,
  size = "sm",
}: {
  buyScore: string;
  buySignalScore: number | null;
  historySpanDays: number;
  // Only used to compute a fallback reference score when there isn't yet
  // enough price history for the real one (see lib/fallbackScore.ts) -
  // safe to omit anywhere that fallback doesn't matter.
  msrp?: number | null;
  currentPrice?: number | null;
  releaseDate?: string | null;
  size?: keyof typeof SIZES;
}) {
  const reliable = buyScore !== "insufficient_data" && historySpanDays >= THIN_DATA_DAYS;
  const fallback = reliable ? null : getFallbackValueScore({ msrp, current_price: currentPrice, release_date: releaseDate });
  const dims = SIZES[size];

  if (reliable) {
    const score = buySignalScore;
    const color = signalColorVar(buyScore);
    const label = SIGNAL_LABELS[buyScore] ?? SIGNAL_LABELS.neutral;
    const pct = score ?? 0;
    return (
      <div className="flex flex-col items-center gap-1.5">
        <div
          className="relative flex items-center justify-center rounded-full"
          style={{
            width: dims.box,
            height: dims.box,
            background:
              score === null
                ? `conic-gradient(var(--border) 0deg, var(--border) 360deg)`
                : `conic-gradient(${color} ${pct * 3.6}deg, var(--border) ${pct * 3.6}deg 360deg)`,
          }}
        >
          <div className="absolute rounded-full bg-card" style={{ inset: dims.ring }} />
          <span className={`relative font-display font-semibold text-foreground ${dims.scoreText}`}>
            {score === null ? "—" : <CountUp value={score} />}
          </span>
        </div>
        <span className={`font-medium uppercase tracking-widest ${dims.labelText}`} style={{ color }}>
          {label}
        </span>
      </div>
    );
  }

  if (fallback) {
    // Deliberately not the same filled conic-gradient ring the real signal
    // uses above - a dashed outline reads as "provisional" at a glance,
    // and the accent color ties into the same FACT/FORECAST visual
    // language used elsewhere on the product page rather than the
    // strong_buy/buy/neutral/not_buy signal colors.
    return (
      <div className="flex flex-col items-center gap-1.5">
        <div
          className="relative flex items-center justify-center rounded-full border-2 border-dashed"
          style={{ width: dims.box, height: dims.box, borderColor: "var(--accent-dark)" }}
        >
          <span className={`relative font-display font-semibold text-foreground ${dims.scoreText}`}>
            <CountUp value={fallback.score} />
          </span>
        </div>
        <span className={`font-medium uppercase tracking-widest ${dims.labelText}`} style={{ color: "var(--accent-dark)" }}>
          {FALLBACK_LABEL}
        </span>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-1.5">
      <div
        className="relative flex items-center justify-center rounded-full"
        style={{ width: dims.box, height: dims.box, background: `conic-gradient(var(--border) 0deg, var(--border) 360deg)` }}
      >
        <div className="absolute rounded-full bg-card" style={{ inset: dims.ring }} />
        <span className={`relative font-display font-semibold text-foreground ${dims.scoreText}`}>—</span>
      </div>
      <span
        className={`font-medium uppercase tracking-widest ${dims.labelText}`}
        style={{ color: signalColorVar("insufficient_data") }}
      >
        {SIGNAL_LABELS.insufficient_data}
      </span>
    </div>
  );
}
