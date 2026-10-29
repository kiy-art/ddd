import FadeIn from "@/components/FadeIn";
import { VERDICTS } from "@/lib/buySignal";

// 2026-10-30 (社長指示「文字が多い。絵で一目でわかるUIに」): the four
// text-paragraph steps became three illustrated steps with one short line
// each, plus a picture of the score scale. The wording of the score bands
// still comes from lib/buySignal.ts so it can never drift from the badges.

function IllustrationRecord() {
  // A week of price points, one per day, filled in left to right.
  const ys = [44, 40, 46, 38, 42, 34, 30];
  return (
    <svg viewBox="0 0 160 90" className="h-full w-full" aria-hidden="true">
      <rect x="8" y="8" width="144" height="74" rx="10" className="fill-white stroke-border dark:fill-card" strokeWidth="1.5" />
      <rect x="8" y="8" width="144" height="16" rx="10" className="fill-brand/10" />
      {["月", "火", "水", "木", "金", "土", "日"].map((d, i) => (
        <text key={d} x={24 + i * 19} y="20" textAnchor="middle" className="fill-foreground/50" fontSize="8">
          {d}
        </text>
      ))}
      <polyline
        points={ys.map((y, i) => `${24 + i * 19},${y + 20}`).join(" ")}
        fill="none"
        className="stroke-brand/40"
        strokeWidth="1.5"
        strokeDasharray="3 3"
      />
      {ys.map((y, i) => (
        <circle key={i} cx={24 + i * 19} cy={y + 20} r="4" className="fill-brand" opacity={0.35 + i * 0.1} />
      ))}
    </svg>
  );
}

function IllustrationCompare() {
  return (
    <svg viewBox="0 0 160 90" className="h-full w-full" aria-hidden="true">
      <path
        d="M12 30 C 34 22, 50 40, 70 32 S 104 36, 120 54 S 140 66, 148 68"
        fill="none"
        className="stroke-brand"
        strokeWidth="2.5"
        strokeLinecap="round"
      />
      <line x1="12" y1="36" x2="148" y2="36" className="stroke-foreground/35" strokeWidth="1.5" strokeDasharray="4 4" />
      <text x="14" y="16" className="fill-foreground/55" fontSize="9">
        30日平均
      </text>
      <line x1="140" y1="39" x2="140" y2="63" className="stroke-sale" strokeWidth="2" markerEnd="url(#how-arrow)" />
      <circle cx="148" cy="68" r="5" className="fill-brand stroke-white" strokeWidth="2" />
      <text x="122" y="84" className="fill-brand font-semibold" fontSize="10">
        安い！
      </text>
      <defs>
        <marker id="how-arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="5" markerHeight="5" orient="auto">
          <path d="M0 0 L10 5 L0 10 Z" className="fill-sale" />
        </marker>
      </defs>
    </svg>
  );
}

function IllustrationScore() {
  // Same arc language as AiBuySignal; 3/4 of a ring = a high score.
  const r = 30;
  const c = 2 * Math.PI * r;
  return (
    <svg viewBox="0 0 160 90" className="h-full w-full" aria-hidden="true">
      <g transform="translate(80 46) rotate(-90)">
        <circle r={r} fill="none" className="stroke-foreground/10" strokeWidth="8" />
        <circle
          r={r}
          fill="none"
          className="stroke-brand"
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={`${c * 0.9} ${c}`}
        />
      </g>
      <text x="80" y="52" textAnchor="middle" className="fill-foreground font-semibold" fontSize="20">
        92
      </text>
    </svg>
  );
}

const STEPS = [
  { n: "1", title: "毎日、価格を記録", line: "ショップの価格を1日1回チェック", art: <IllustrationRecord /> },
  { n: "2", title: "平均とくらべる", line: "過去30日より安いかを判定", art: <IllustrationCompare /> },
  { n: "3", title: "買い時を数字で", line: "1〜99のスコアでひと目でわかる", art: <IllustrationScore /> },
];

// Low → high, left → right, so the bar reads like a thermometer.
const SCALE = [
  { key: "not_buy", tone: "bg-signal-low/40", flex: 39 },
  { key: "neutral", tone: "bg-signal-mid/50", flex: 25 },
  { key: "buy", tone: "bg-brand/60", flex: 15 },
  { key: "strong_buy", tone: "bg-brand", flex: 20 },
] as const;

export default function HowItWorks() {
  return (
    <section id="how-it-works" className="border-t border-border bg-background px-6 py-20 sm:py-28">
      <div className="mx-auto max-w-7xl">
        <FadeIn>
          <span className="text-xs font-medium uppercase tracking-[0.3em] text-accent">How It Works</span>
          <h2 className="mt-3 font-display text-3xl font-semibold leading-tight text-foreground sm:text-4xl">
            <span className="inline-block">3ステップで</span>
            <span className="inline-block">「買い時」がわかる</span>
          </h2>
        </FadeIn>

        <ol className="mt-10 grid grid-cols-1 gap-4 sm:mt-14 sm:grid-cols-3 sm:gap-6">
          {STEPS.map((step, i) => (
            <FadeIn key={step.n} delay={i * 80}>
              <li className="relative flex h-full flex-col items-center rounded-2xl border border-border bg-card p-5 text-center sm:p-6">
                <span className="absolute left-4 top-4 flex h-7 w-7 items-center justify-center rounded-full bg-brand font-num text-sm font-semibold text-white">
                  {step.n}
                </span>
                <div className="h-24 w-40 sm:h-28 sm:w-48">{step.art}</div>
                <h3 className="mt-3 font-display text-lg font-semibold text-foreground">{step.title}</h3>
                <p className="mt-1 text-sm text-foreground/60">{step.line}</p>
                {i < STEPS.length - 1 && (
                  <span
                    aria-hidden="true"
                    className="absolute -bottom-4 left-1/2 z-10 flex h-7 w-7 -translate-x-1/2 items-center justify-center rounded-full border border-border bg-background text-brand sm:-right-5 sm:bottom-auto sm:left-auto sm:top-1/2 sm:-translate-y-1/2 sm:translate-x-0"
                  >
                    <span className="sm:hidden">↓</span>
                    <span className="hidden sm:inline">→</span>
                  </span>
                )}
              </li>
            </FadeIn>
          ))}
        </ol>

        <FadeIn delay={240}>
          <figure className="mt-12 rounded-2xl border border-border bg-card p-5 sm:p-6">
            <figcaption className="mb-4 text-sm font-semibold text-foreground">スコアの見方</figcaption>
            <div className="flex h-3 overflow-hidden rounded-full">
              {SCALE.map((s) => (
                <div key={s.key} className={s.tone} style={{ flex: s.flex }} />
              ))}
            </div>
            <div className="mt-3 flex text-center">
              {SCALE.map((s) => (
                <div key={s.key} style={{ flex: s.flex }} className="min-w-0 px-0.5">
                  <div
                    className={`truncate text-[11px] font-semibold sm:text-sm ${
                      s.key === "strong_buy" || s.key === "buy" ? "text-brand" : "text-foreground/60"
                    }`}
                  >
                    {VERDICTS[s.key].label}
                  </div>
                  <div className="font-num text-[10px] text-foreground/45 sm:text-xs">{VERDICTS[s.key].range}</div>
                </div>
              ))}
            </div>
            <p className="mt-4 text-[11px] text-foreground/45">記録した価格にもとづく目安です。将来の価格を保証するものではありません。</p>
          </figure>
        </FadeIn>
      </div>
    </section>
  );
}
