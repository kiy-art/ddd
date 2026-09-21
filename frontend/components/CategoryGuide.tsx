const GUIDES: Record<string, { picking: string; timing: string }> = {
  driver: {
    picking:
      "ヘッド体積・ロフト角・シャフトの硬さ（フレックス）の組み合わせで弾道は大きく変わります。スイングスピードが速いほど硬めのシャフトやロフトが小さいモデルが合いやすく、逆に非力な場合は柔らかめのシャフトとロフトが大きいモデルの方が安定しやすい傾向があります。",
    timing:
      "ドライバーは主要メーカーの新モデルが年1回ペースで出るのが一般的です。新モデル発売直後は型落ちモデルが値下がりしやすく、性能差が体感しにくいプレーヤーであれば型落いを狙うのも有力な選択肢です。",
  },
  iron: {
    picking:
      "アイアンは「飛距離重視のキャビティ系」と「操作性重視のマッスルバック系」に大別されます。番手構成（何番から何番までのセットか）や、シャフトが純正カーボンかスチールかによっても価格・打感が変わります。",
    timing:
      "アイアンのモデルチェンジ周期はドライバーよりやや長めです。フルセットは価格が張るため、型落ちモデルのセット割引や単品バラ売りを狙うと総額を抑えやすくなります。",
  },
  wedge: {
    picking:
      "ロフト角（52度・56度・58度など）とバンス角の組み合わせが、コース状況やスイングタイプとの相性を左右します。手持ちのアイアンとのロフト間隔（ギャッピング）を揃えることも重要です。",
    timing:
      "ウェッジはモデルチェンジの周期が緩やかで、季節による価格変動もドライバー・アイアンほど大きくありません。焦らずセール時期を待って購入しても選択肢が狭まりにくいカテゴリです。",
  },
  putter: {
    picking:
      "ヘッド形状（マレット型 or ピン型）、長さ、ライ角の合い方でストローク中の構えやすさが変わります。ツアー選手の使用実績があるモデルは中古相場も安定しやすい傾向があります。",
    timing:
      "パターは年間を通じて新製品が出るため「型落ちを待つ」効果はドライバーほど大きくありません。むしろ試打して構えやすさを確認できるタイミングを優先する方が選びやすいカテゴリです。",
  },
  ball: {
    picking:
      "ディンプル構造とコア（芯材）の圧縮率（コンプレッション）で、スピン量と弾道の高さが変わります。ヘッドスピードが遅めなら低圧縮、速めなら高圧縮のモデルが噛み合いやすい傾向があります。",
    timing:
      "ボールは消耗品のためモデルチェンジを待つ意味は薄く、複数ダースまとめ買いできるセール（年末年始など）を狙うのが最も効果的な節約方法です。",
  },
};

export default function CategoryGuide({ category }: { category: string }) {
  const guide = GUIDES[category];
  if (!guide) return null;

  return (
    <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
      <div className="rounded-2xl border border-border bg-card p-6 sm:p-8">
        <span className="text-xs font-medium uppercase tracking-[0.3em] text-accent">How To Choose</span>
        <h2 className="mt-2 font-display text-xl font-semibold text-foreground">選び方のポイント</h2>
        <p className="mt-3 text-sm leading-relaxed text-foreground/60">{guide.picking}</p>
      </div>
      <div className="rounded-2xl border border-border bg-card p-6 sm:p-8">
        <span className="text-xs font-medium uppercase tracking-[0.3em] text-accent">When To Buy</span>
        <h2 className="mt-2 font-display text-xl font-semibold text-foreground">型落ちと最新モデル、どちらを選ぶ？</h2>
        <p className="mt-3 text-sm leading-relaxed text-foreground/60">{guide.timing}</p>
      </div>
    </div>
  );
}
