import CountUp from "@/components/CountUp";
import { NEW_LISTING, SCORE_NAME, verdictInfo } from "@/lib/buySignal";
import { getFallbackValueScore } from "@/lib/fallbackScore";

// A separate, deliberately different-sounding label from the real verdict
// labels (lib/buySignal.ts) - this number is not the same kind of claim
// (see lib/fallbackScore.ts), so it must never look like one.
const FALLBACK_LABEL = "定価からのお得度";

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
  sm: { box: 56, ring: 5, scoreText: "text-base", labelText: "text-[10px]" },
  lg: { box: 108, ring: 7, scoreText: "text-3xl", labelText: "text-xs" },
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
    const verdict = verdictInfo(buyScore);
    const pct = score ?? 0;
    const description =
      score === null
        ? `${SCORE_NAME}: ${verdict.label}`
        : `${SCORE_NAME} ${score}/100: ${verdict.label}（${verdict.meaning}）`;
    // Buy verdicts get an emerald gradient sweep with a soft glow (and a
    // slow "breathing" halo for 今が買い時); hold/wait stay a flat, quiet
    // ring so the eye only lands where there's something to act on.
    const positive = buyScore === "strong_buy" || buyScore === "buy";
    const sweep = pct * 3.6;
    const ringFill =
      score === null
        ? `conic-gradient(var(--border) 0deg, var(--border) 360deg)`
        : positive
          ? `conic-gradient(from 200deg, var(--brand-dark) 0deg, var(--brand-light) ${sweep}deg, color-mix(in srgb, var(--foreground) 9%, transparent) ${sweep}deg 360deg)`
          : `conic-gradient(${color} ${sweep}deg, color-mix(in srgb, var(--foreground) 9%, transparent) ${sweep}deg 360deg)`;
    return (
      <div className="flex flex-col items-center gap-1.5" title={description} aria-label={description} role="img">
        <div
          className={`relative flex items-center justify-center rounded-full ${buyScore === "strong_buy" ? "score-breathe" : ""}`}
          style={{
            width: dims.box,
            height: dims.box,
            background: ringFill,
            boxShadow: positive && buyScore !== "strong_buy" ? "0 0 20px -8px rgba(var(--glow), 0.6)" : undefined,
          }}
        >
          <div className="absolute rounded-full bg-card" style={{ inset: dims.ring }} />
          <span className={`font-num relative flex items-baseline font-semibold text-foreground ${dims.scoreText}`}>
            {score === null ? "—" : <CountUp value={score} />}
            {score !== null && size === "lg" && <span className="ml-0.5 text-xs font-medium text-foreground/40">/100</span>}
          </span>
        </div>
        <span className={`whitespace-nowrap font-semibold ${dims.labelText}`} style={{ color }}>
          {verdict.label}
        </span>
        {size === "lg" && <span className="text-[10px] text-foreground/40">{SCORE_NAME}</span>}
      </div>
    );
  }

  if (fallback) {
    // Deliberately not the same filled conic-gradient ring the real signal
    // uses above - a dashed outline reads as "provisional" at a glance,
    // and the accent color ties into the same FACT/FORECAST visual
    // language used elsewhere on the product page rather than the
    // strong_buy/buy/neutral/not_buy signal colors.
    const fallbackDescription = `${FALLBACK_LABEL} ${fallback.score}/100（価格の記録がまだ少ないため、定価と比べた目安です）`;
    return (
      <div className="flex flex-col items-center gap-1.5" title={fallbackDescription} aria-label={fallbackDescription} role="img">
        <div
          className="relative flex items-center justify-center rounded-full border-2 border-dashed"
          style={{ width: dims.box, height: dims.box, borderColor: "var(--accent-dark)" }}
        >
          <span className={`font-num relative font-semibold text-foreground ${dims.scoreText}`}>
            <CountUp value={fallback.score} />
          </span>
        </div>
        <span className={`whitespace-nowrap font-semibold ${dims.labelText}`} style={{ color: "var(--accent-dark)" }}>
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
        <span className={`font-num relative font-semibold text-foreground ${dims.scoreText}`}>—</span>
      </div>
      <span
        className={`whitespace-nowrap font-semibold ${dims.labelText}`}
        style={{ color: signalColorVar("insufficient_data") }}
        title={NEW_LISTING.meaning}
      >
        {NEW_LISTING.label}
      </span>
    </div>
  );
}
