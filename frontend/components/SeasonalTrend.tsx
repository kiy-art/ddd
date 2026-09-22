const SEASONAL_NOTES: Record<string, string> = {
  driver:
    "ドライバーは例年1〜3月に主要メーカーの新モデルが発売される傾向があります。新モデル発売の直前・直後（12月〜4月頃）は、型落ちモデルの値下がりが起こりやすい時期です。",
  iron:
    "アイアンも春先（1〜3月）にモデルチェンジが集中する傾向があります。型落ちモデルは新モデル発売後の数ヶ月で価格が動きやすくなります。",
  wedge:
    "ウェッジはドライバー・アイアンに比べてモデルチェンジの周期が緩やかで、季節による価格変動は比較的小さい傾向があります。年末年始やボーナス商戦明けのセールで動くことがあります。",
  putter:
    "パターは年間を通じて発売されますが、ツアーでの使用開始に合わせた1〜2月の発表が多い傾向があります。型落ちモデルはその後値下がりしやすくなります。",
  ball:
    "ゴルフボールは他カテゴリに比べて季節性が小さく、年間を通じて需要が安定しています。上位モデルのモデルチェンジ（春頃）や年末セールのタイミングで価格が動くことがあります。",
};

export default function SeasonalTrend({ category }: { category: string }) {
  const note = SEASONAL_NOTES[category];
  if (!note) return null;

  return (
    <div>
      <span className="text-xs font-medium uppercase tracking-[0.3em] text-accent">Seasonal Pattern</span>
      <h3 className="mt-2 font-display text-lg font-semibold text-foreground">一般的な季節傾向（カテゴリ全体）</h3>
      <p className="mt-3 text-sm leading-relaxed text-foreground/60">{note}</p>
      <p className="mt-4 text-xs text-foreground/35">
        ※これはこの商品固有の値下がり予測ではなく、ゴルフ業界全般の一般的な傾向に関する参考情報です。
        実際の値動きを保証するものではありません。商品固有の傾向分析は、価格データが十分に蓄積された後に提供予定です。
      </p>
    </div>
  );
}
