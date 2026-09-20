import FadeIn from "@/components/FadeIn";

const STEPS = [
  {
    n: "01",
    title: "価格を毎日記録",
    body: "登録されたゴルフ用品の価格を毎日収集し、過去の推移としてデータベースに蓄積します。",
  },
  {
    n: "02",
    title: "AIが統計分析",
    body: "過去30日の平均・最高値と現在価格を比較し、ルールベースの統計で買い時かどうかを判定します。",
  },
  {
    n: "03",
    title: "スコアとして提示",
    body: "判定結果を「AI BUY SIGNAL」スコアに変換。数字を見るだけで買い時度が直感的に分かります。",
  },
  {
    n: "04",
    title: "毎日更新",
    body: "価格が変わるたびにスコアも自動で更新。常に最新の「買い時」を届け続けます。",
  },
];

export default function HowItWorks() {
  return (
    <section id="how-it-works" className="border-t border-border bg-background px-6 py-24 sm:py-32">
      <div className="mx-auto max-w-7xl">
        <FadeIn>
          <span className="text-xs font-medium uppercase tracking-[0.3em] text-accent">How It Works</span>
          <h2 className="mt-3 max-w-lg font-display text-3xl font-semibold leading-tight text-foreground sm:text-4xl">
            仕組みはシンプルに、
            <br />
            判断はAIに。
          </h2>
        </FadeIn>

        <div className="mt-16 grid grid-cols-1 gap-10 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((step, i) => (
            <FadeIn key={step.n} delay={i * 80}>
              <div className="flex flex-col gap-3 border-t border-border pt-5">
                <span className="font-display text-sm text-accent">{step.n}</span>
                <h3 className="font-display text-lg font-medium text-foreground">{step.title}</h3>
                <p className="text-sm leading-relaxed text-foreground/55">{step.body}</p>
              </div>
            </FadeIn>
          ))}
        </div>
      </div>
    </section>
  );
}
