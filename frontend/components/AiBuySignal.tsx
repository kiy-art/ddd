import CountUp from "@/components/CountUp";

const SIGNAL_LABELS: Record<string, string> = {
  strong_buy: "STRONG BUY",
  buy: "BUY NOW",
  neutral: "HOLD",
  not_buy: "WAIT",
  insufficient_data: "ANALYZING",
};

function computeScore(buyScore: string, pct: number | null): number | null {
  if (buyScore === "insufficient_data" || pct === null) return null;
  const raw = 50 - pct * 2;
  return Math.max(1, Math.min(99, Math.round(raw)));
}

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
  priceChangePercent,
  size = "sm",
}: {
  buyScore: string;
  priceChangePercent: number | null;
  size?: keyof typeof SIZES;
}) {
  const score = computeScore(buyScore, priceChangePercent);
  const color = signalColorVar(buyScore);
  const label = SIGNAL_LABELS[buyScore] ?? SIGNAL_LABELS.neutral;
  const dims = SIZES[size];
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
        <div
          className="absolute rounded-full bg-card"
          style={{ inset: dims.ring }}
        />
        <span className={`relative font-display font-semibold text-foreground ${dims.scoreText}`}>
          {score === null ? "—" : <CountUp value={score} />}
        </span>
      </div>
      <span
        className={`font-medium uppercase tracking-widest ${dims.labelText}`}
        style={{ color }}
      >
        {label}
      </span>
    </div>
  );
}
