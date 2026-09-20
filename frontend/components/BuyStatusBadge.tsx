import { BUY_SCORE_LABELS } from "@/lib/api";

const STYLES: Record<string, string> = {
  strong_buy: "bg-signal-high text-white",
  buy: "bg-signal-high/80 text-white",
  neutral: "bg-signal-mid text-white",
  not_buy: "border border-border text-foreground/60",
  insufficient_data: "border border-dashed border-border text-foreground/35",
};

export default function BuyStatusBadge({ buyScore }: { buyScore: string }) {
  const style = STYLES[buyScore] ?? STYLES.neutral;
  const label = BUY_SCORE_LABELS[buyScore] ?? buyScore;
  return (
    <span className={`inline-block shrink-0 rounded-full px-3 py-1 text-xs font-semibold ${style}`}>
      {label}
    </span>
  );
}
