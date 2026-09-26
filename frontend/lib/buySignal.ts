// What the 買い時スコア (buy_signal_score) means, in one place - every page
// that shows the number takes its wording from here.
//
// Since STEP49 the backend places the score inside its verdict's band
// (backend/app/analysis.py SCORE_BANDS), so the number and the label can
// never contradict each other: 80+ is always "今が買い時", never "様子見".

export interface VerdictInfo {
  label: string; // shown next to the number
  meaning: string; // one plain sentence: what to do
  range: string; // the score band, e.g. "80〜99"
}

export const VERDICTS: Record<string, VerdictInfo> = {
  strong_buy: { label: "今が買い時", meaning: "過去の価格と比べてかなり安い水準です", range: "80〜99" },
  buy: { label: "買い時", meaning: "過去の価格と比べて安い水準です", range: "65〜79" },
  neutral: { label: "様子見", meaning: "平均的な価格です。急ぎでなければ値下がりを待つ手もあります", range: "40〜64" },
  not_buy: { label: "待つのが無難", meaning: "最近の中では高めの価格です", range: "1〜39" },
};

export const NEW_LISTING: VerdictInfo = {
  label: "データ収集中",
  meaning: "価格の記録を始めたばかりで、まだ判定できません",
  range: "",
};

export const SCORE_NAME = "買い時スコア";

// Plain-language description used in tooltips/aria labels and the FAQ.
export const SCORE_EXPLANATION =
  "買い時スコアは、PAR.が毎日記録している実際の価格から「今の価格が過去と比べてどれだけお得か」を1〜99で表した目安です。高いほど買い時です（80以上：今が買い時／65〜79：買い時／40〜64：様子見／39以下：待つのが無難）。将来の値動きを保証するものではありません。";

export function verdictInfo(buyScore: string): VerdictInfo {
  return VERDICTS[buyScore] ?? NEW_LISTING;
}

/**
 * The verdict's one-line meaning, made specific where the generic sentence
 * would contradict the facts listed right under it: a "様子見" product can
 * be at its recorded low yet only a few % under its 30-day average (the
 * verdict needs a 10% gap - backend analysis.BUY_RATIO). Saying "平均的な
 * 価格です" there would read as wrong next to "記録している中で最も安い".
 */
export function verdictMeaning(p: {
  buy_score: string;
  current_price: number | null;
  lowest_price: number | null;
  price_change_percent: number | null;
}): string {
  const base = verdictInfo(p.buy_score).meaning;
  const atLowest = p.current_price !== null && p.lowest_price !== null && p.current_price <= p.lowest_price;
  if (p.buy_score === "neutral" && atLowest && p.price_change_percent !== null) {
    return `記録上の最安値ですが、30日平均との差は${Math.abs(p.price_change_percent)}%と小さく、「買い時」と判定する目安（平均より10%以上安い）には届いていません`;
  }
  return base;
}

export interface ScoreReason {
  text: string;
  good: boolean; // points toward "buy"
}

/**
 * The real facts behind today's score - the same four signals the backend
 * weighs (analysis._buy_signal_score), stated as numbers a shopper can
 * check against the price chart on the same page. Only facts actually
 * available are returned; nothing is estimated.
 */
export function scoreReasons(p: {
  current_price: number | null;
  average_price: number | null;
  lowest_price: number | null;
  price_change_percent: number | null;
  price_history: { price: number; recorded_at: string }[];
}): ScoreReason[] {
  const reasons: ScoreReason[] = [];
  const current = p.current_price;
  if (current === null) return reasons;

  if (p.price_change_percent !== null && p.average_price !== null) {
    const pct = p.price_change_percent;
    if (pct < 0) {
      reasons.push({ text: `30日平均（¥${p.average_price.toLocaleString("ja-JP")}）より${Math.abs(pct)}%安い`, good: true });
    } else if (pct > 0) {
      reasons.push({ text: `30日平均（¥${p.average_price.toLocaleString("ja-JP")}）より${pct}%高い`, good: false });
    } else {
      reasons.push({ text: "30日平均と同じ価格", good: false });
    }
  }

  if (p.lowest_price !== null) {
    if (current <= p.lowest_price) {
      reasons.push({ text: "記録している中で最も安い価格", good: true });
    } else {
      const gap = Math.round(((current - p.lowest_price) / p.lowest_price) * 1000) / 10;
      reasons.push({ text: `記録上の最安値（¥${p.lowest_price.toLocaleString("ja-JP")}）より${gap}%高い`, good: gap <= 5 });
    }
  }

  // 7-day movement, from the same price history the chart shows.
  const history = [...p.price_history].sort((a, b) => toTime(a.recorded_at) - toTime(b.recorded_at));
  const latest = history.length > 0 ? toTime(history[history.length - 1].recorded_at) : null;
  if (latest !== null) {
    const weekAgo = latest - 7 * 24 * 60 * 60 * 1000;
    const older = history.filter((h) => toTime(h.recorded_at) <= weekAgo);
    const base = older.length > 0 ? older[older.length - 1].price : null;
    if (base !== null && base > 0) {
      const change = Math.round(((current - base) / base) * 1000) / 10;
      if (change < 0) reasons.push({ text: `この7日間で${Math.abs(change)}%値下がり`, good: true });
      else if (change > 0) reasons.push({ text: `この7日間で${change}%値上がり`, good: false });
      else reasons.push({ text: "この7日間は価格の変動なし", good: false });
    }
  }
  return reasons;
}

// Backend timestamps are naive UTC ("2026-09-25T00:48:09") - parse as UTC.
function toTime(value: string): number {
  const hasZone = /Z$|[+-]\d{2}:?\d{2}$/.test(value);
  return new Date(value.includes("T") && !hasZone ? `${value}Z` : value).getTime();
}
