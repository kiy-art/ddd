// 2026-10-30 (社長指示「季節傾向もグラフ化」): the paragraph per category
// became a 12-month strip. Only months the old text actually named are
// marked - nothing here is a per-product prediction or a new claim.
type Season = {
  launch: number[]; // months the text says new models tend to come out
  move: number[]; // months the text says prices tend to move / sales happen
  caption: string;
};

const SEASONS: Record<string, Season> = {
  driver: { launch: [1, 2, 3], move: [12, 1, 2, 3, 4], caption: "新モデル発売の前後（12〜4月頃）は型落ちが値下がりしやすい" },
  iron: { launch: [1, 2, 3], move: [], caption: "新モデル発売後の数ヶ月は型落ちの価格が動きやすい" },
  wedge: { launch: [], move: [12, 1], caption: "季節の変動は小さめ。年末年始のセールで動くことも" },
  putter: { launch: [1, 2], move: [], caption: "発表は1〜2月が多く、その後型落ちが値下がりしやすい" },
  ball: { launch: [3, 4], move: [12], caption: "季節の変動は小さめ。春のモデルチェンジと年末セールで動くことも" },
};

export default function SeasonalTrend({ category }: { category: string }) {
  const season = SEASONS[category];
  if (!season) return null;

  return (
    <div>
      <span className="text-xs font-medium uppercase tracking-[0.3em] text-accent">Seasonal Pattern</span>
      <h3 className="mt-2 font-display text-lg font-semibold text-foreground">一般的な季節傾向（カテゴリ全体）</h3>

      <div
        className="mt-4 grid grid-cols-12 gap-1"
        role="img"
        aria-label={`新モデルが出やすい月：${season.launch.join("・") || "目立った時期なし"}月。価格が動きやすい月：${season.move.join("・") || "—"}月。${season.caption}`}
      >
        {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => {
          const launch = season.launch.includes(m);
          const move = season.move.includes(m);
          return (
            <div key={m} className="flex flex-col items-center gap-1">
              <div
                className={`flex h-10 w-full items-center justify-center rounded-md text-sm sm:h-12 ${
                  move ? "bg-brand/80 text-white" : launch ? "bg-brand/20" : "bg-foreground/5"
                }`}
              >
                {launch ? "🆕" : ""}
              </div>
              <span className="font-num text-[10px] text-foreground/50">{m}</span>
            </div>
          );
        })}
      </div>

      <div aria-hidden="true" className="mt-3 flex flex-wrap gap-3 text-[11px] text-foreground/60">
        <span className="text-foreground/45">数字＝月</span>
        {season.launch.length > 0 && (
          <span className="inline-flex items-center gap-1.5">
            <span>🆕</span>新モデルが出やすい
          </span>
        )}
        {season.move.length > 0 && (
          <span className="inline-flex items-center gap-1.5">
            <span className="h-3 w-3 rounded-sm bg-brand/80" />価格が動きやすい
          </span>
        )}
      </div>
      <p className="mt-3 text-sm font-medium text-foreground/75">{season.caption}</p>
      <p className="mt-2 text-[11px] text-foreground/40">
        ※ゴルフ業界全般の一般的な傾向で、この商品の値動きの予測・保証ではありません。
      </p>
    </div>
  );
}
