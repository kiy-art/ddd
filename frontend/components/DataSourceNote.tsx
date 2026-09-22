const SOURCES: { label: string; detail: string }[] = [
  { label: "現在価格・価格履歴", detail: "楽天市場の商品検索APIから1日1回自動取得しています。" },
  {
    label: "メーカー希望小売価格・発売日・スキルレベル等",
    detail: "メーカー公式サイトや製品リリースをもとに編集部が個別に調査・入力した情報です（自動更新ではありません）。",
  },
  { label: "買い時判定・価格予測", detail: "上記の実データのみを使い、あらかじめ決めたルールで機械的に算出しています。AIによる作文はあくまで結果の説明に使うのみで、判定そのものには影響しません。" },
  { label: "人気ランキング", detail: "楽天市場のカテゴリ別ベストセラーランキングを参照しています。" },
];

/**
 * Plain, factual "where does this number come from" section - exists so
 * the honesty stance the rest of the page takes (FACT/FORECAST labels,
 * "データ不足" instead of fabricated numbers) is backed by something the
 * reader can actually check, not just a claim.
 */
export default function DataSourceNote() {
  return (
    <div className="rounded-2xl border border-border bg-card p-6 sm:p-8">
      <span className="text-xs font-medium uppercase tracking-[0.3em] text-accent">Data Source</span>
      <h2 className="mt-2 font-display text-xl font-semibold text-foreground">このページのデータについて</h2>
      <dl className="mt-4 flex flex-col gap-3 text-sm">
        {SOURCES.map((s) => (
          <div key={s.label}>
            <dt className="font-medium text-foreground/80">{s.label}</dt>
            <dd className="mt-0.5 text-foreground/50">{s.detail}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
