// A second, deliberately separate fallback from lib/fallbackScore.ts: that
// file needs msrp to say anything; this one needs only release_date (or,
// stronger still, the manually-researched is_current_generation fact) - so
// a product with no MSRP on file can still get a real, honest "buy timing"
// read instead of nothing.
//
// Golf-specific on purpose (unlike fallbackScore.ts, which stays genre-
// agnostic): the "~1-2 year model cycle" reasoning below is a real,
// golf-industry-specific pattern, the same one already used for
// SeasonalTrend's category text - see ai_company_guidelines.md 3.4 for the
// standing note that this kind of category-specific text is a known,
// accepted seam for a future non-golf vertical, not something to solve here.

export type ModelCycleTier = "fact" | "estimate";

export interface ModelCycleInsight {
  // "fact": backed by a manually-researched, confirmed field
  // (is_current_generation) - not a guess.
  // "estimate": inferred purely from elapsed time since release, using a
  // general industry pattern - never billed as if it were per-product data.
  tier: ModelCycleTier;
  stageLabel: string;
  message: string;
  monthsSinceRelease: number | null;
}

export const MODEL_CYCLE_DISCLAIMER =
  "※この商品固有のデータではなく、ゴルフ用品一般のモデルチェンジ傾向（発売からおよそ1〜2年周期）に基づくAIの推測です。将来の値下がりを保証するものではありません。";

export const MODEL_CYCLE_FACT_NOTE = "※メーカー公式情報等をもとに編集部が確認した事実です。将来の値下がりを保証するものではありません。";

function monthsSince(dateStr: string): number {
  const elapsedMs = Date.now() - new Date(dateStr).getTime();
  return elapsedMs / (1000 * 60 * 60 * 24 * 30.44);
}

export function getModelCycleInsight(product: {
  release_date: string | null;
  is_current_generation: boolean | null;
}): ModelCycleInsight | null {
  // The strongest, most reliable signal available: a researched fact, not
  // an inference - a confirmed successor model already exists.
  if (product.is_current_generation === false) {
    return {
      tier: "fact",
      stageLabel: "型落ちモデル",
      message: "既に後継モデルが発売されている型落ちモデルです。今後も値下がりが進みやすい傾向があります。",
      monthsSinceRelease: product.release_date ? monthsSince(product.release_date) : null,
    };
  }

  if (!product.release_date) return null;
  const months = monthsSince(product.release_date);

  if (months < 6) {
    return {
      tier: "estimate",
      stageLabel: "発売直後",
      message: "発売から間もないため、値下がりはまだ限定的とみられます。",
      monthsSinceRelease: months,
    };
  }
  if (months < 12) {
    return {
      tier: "estimate",
      stageLabel: "値下がり傾向入り",
      message: "一般的なモデルチェンジ周期（約1〜2年）に近づいており、今後じわじわ値下がりが進みやすい時期です。",
      monthsSinceRelease: months,
    };
  }
  if (months < 24) {
    return {
      tier: "estimate",
      stageLabel: "型落ち間近",
      message: "モデルチェンジの目安とされる期間に入っており、後継モデル発表とともに値下がりが進む可能性があります。",
      monthsSinceRelease: months,
    };
  }
  return {
    tier: "estimate",
    stageLabel: "底値圏の可能性",
    message: "一般的なモデルチェンジ周期を超えており、価格が底値圏に近づいている可能性があります。",
    monthsSinceRelease: months,
  };
}
