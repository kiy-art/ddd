// Turns a raw price delta into the one-line sentence a shopper actually
// wants ("定価より16%安い"), instead of making them do the subtraction
// themselves from two stacked numbers. Never fabricates a reference point:
// callers only pass in real values (MSRP or the 30-day average) that are
// already known to be non-null.
export interface PriceComparison {
  label: string;
  direction: "down" | "up" | "flat";
  percent: number;
}

export function comparePrice(current: number, reference: number, referenceLabel: string): PriceComparison | null {
  if (reference <= 0) return null;
  const diffPercent = Math.round(((current - reference) / reference) * 1000) / 10;
  if (diffPercent === 0) return { label: `${referenceLabel}と同じ価格`, direction: "flat", percent: 0 };
  const direction = diffPercent < 0 ? "down" : "up";
  const abs = Math.abs(diffPercent);
  return {
    label: `${referenceLabel}より${abs}%${direction === "down" ? "安い" : "高い"}`,
    direction,
    percent: abs,
  };
}
