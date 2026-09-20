import { BUY_SCORE_LABELS } from "@/lib/api";

const STYLES: Record<string, string> = {
  strong_buy: "bg-red-600 text-white shadow-sm shadow-red-600/30",
  buy: "bg-accent text-white shadow-sm shadow-accent/30",
  neutral: "bg-zinc-400 text-white",
  not_buy: "bg-zinc-200 text-zinc-600 dark:bg-zinc-700 dark:text-zinc-300",
  insufficient_data: "bg-zinc-100 text-zinc-400 dark:bg-zinc-800 dark:text-zinc-500",
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
