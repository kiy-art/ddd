import { BUY_SCORE_LABELS } from "@/lib/api";

const STYLES: Record<string, string> = {
  strong_buy: "bg-red-600 text-white",
  buy: "bg-orange-500 text-white",
  neutral: "bg-zinc-400 text-white",
  not_buy: "bg-zinc-200 text-zinc-700",
  insufficient_data: "bg-zinc-100 text-zinc-500",
};

export default function BuyStatusBadge({ buyScore }: { buyScore: string }) {
  const style = STYLES[buyScore] ?? STYLES.neutral;
  const label = BUY_SCORE_LABELS[buyScore] ?? buyScore;
  return (
    <span className={`inline-block rounded-full px-3 py-1 text-xs font-semibold ${style}`}>
      {label}
    </span>
  );
}
