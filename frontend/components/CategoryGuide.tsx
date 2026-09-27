// timingHeading: only where the default "型落ちと最新モデル" framing doesn't
// fit (a glove is a consumable - the question is when to restock).
const GUIDES: Record<string, { picking: string; timing: string; timingHeading?: string }> = {
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
  // STEP55: general buying guidance only - no model-specific or
  // market-data claims (those come from the price data on each page).
  glove: {
    timingHeading: "買い足しのタイミング",
    picking:
      "グローブはサイズ（cm表記）が合っていることが最優先です。指先が余ると握りがゆるみ、きついと破れやすくなります。天然皮革は手になじみやすく、合成皮革は耐久性や雨・汗への強さで選ばれることが多い素材です。雨の日用や冬用など、用途を限定したモデルもあります。",
    timing:
      "グローブは使うほど傷む消耗品なので、モデルチェンジを待つより、手持ちが傷む前に買い足すのが基本です。同じモデル・同じサイズを複数枚まとめて買う人も多く、価格が下がっているときにまとめて買うと1枚あたりを抑えやすくなります。",
  },
  rangefinder: {
    picking:
      "ピンまでの距離をレーザーで測るタイプと、GPSでコース上の位置から測るタイプがあります。レーザー式は目標を狙って測れるのが特長で、手ブレ補正やピンを捉えたときに振動で知らせる機能などで使い勝手が変わります。高低差を加味した距離を表示する機能は、競技によっては使用が認められない場合があるため、出場予定の競技の規則を確認しておくと安心です。",
    timing:
      "距離計は長く使う機器なので、必要な機能を先に決めてから、その機能を持つモデルの中で価格を比べるのが選びやすい方法です。新しいモデルが出ると、以前のモデルの価格が動くことがあります。",
  },
  // STEP63: pins, markers, forks, tees and practice gear - general guidance only.
  other: {
    timingHeading: "買い足しのタイミング",
    picking:
      "マーカーやグリーンフォークは、ポケットやキャップに付けて持ち歩くものなので、大きさ・重さと取り付け方（クリップ・マグネットなど）で選ぶと使いやすくなります。ティーは長さと素材（木製・プラスチック）で選び、ドライバー用は長め、アイアン用は短めが一般的です。練習用のピンフラッグやカップは、置く場所の広さに合うサイズを確認しておくと安心です。",
    timing:
      "小物はなくしたり消耗したりしやすいので、必要になる前にまとめて買い足しておくのが基本です。単価が低い分、送料で割高になりやすいため、ほかの買い物とまとめる、送料無料になる数量で買うなどの工夫が効果的です。",
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
        <h2 className="mt-2 font-display text-xl font-semibold text-foreground">
          {guide.timingHeading ?? "型落ちと最新モデル、どちらを選ぶ？"}
        </h2>
        <p className="mt-3 text-sm leading-relaxed text-foreground/60">{guide.timing}</p>
      </div>
    </div>
  );
}
