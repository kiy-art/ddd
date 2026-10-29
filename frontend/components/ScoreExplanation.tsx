import { VERDICTS, SCORE_NAME, scoreReasons, verdictInfo } from "@/lib/buySignal";
import type { ProductDetail } from "@/lib/api";

// "What does this number mean?" - shown under the score ring on the product
// page. 2026-10-30 (社長指示「製品ページも文字が多い」): the sentence +
// bullet list + text legend became a score bar with a marker, and the real
// facts behind the number as ✓/− rows. Wording still comes from
// lib/buySignal.ts; only rendered when the score rests on enough history.
const SCALE = [
  { key: "not_buy", tone: "bg-signal-low/40", from: 1, to: 39 },
  { key: "neutral", tone: "bg-signal-mid/50", from: 40, to: 64 },
  { key: "buy", tone: "bg-brand/60", from: 65, to: 79 },
  { key: "strong_buy", tone: "bg-brand", from: 80, to: 99 },
] as const;

export default function ScoreExplanation({ product }: { product: ProductDetail }) {
  const verdict = verdictInfo(product.buy_score);
  const reasons = scoreReasons(product);
  const score = Math.min(99, Math.max(1, product.buy_signal_score ?? 1));

  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-border bg-card p-5">
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-xs font-medium text-foreground/50">{SCORE_NAME}</span>
        <span className="text-sm font-semibold text-foreground">
          <span className="font-num text-lg">{product.buy_signal_score}</span>
          <span className="text-foreground/45">/100</span>
          <span className="ml-2 text-brand dark:text-brand-light">{verdict.label}</span>
        </span>
      </div>

      <div role="img" aria-label={`${SCORE_NAME}${product.buy_signal_score}：${verdict.label}`}>
        <div className="relative">
          <div className="flex h-2.5 overflow-hidden rounded-full">
            {SCALE.map((s) => (
              <div key={s.key} className={s.tone} style={{ flex: s.to - s.from + 1 }} />
            ))}
          </div>
          <span
            aria-hidden="true"
            className="absolute top-1/2 h-5 w-5 -translate-x-1/2 -translate-y-1/2 rounded-full border-[3px] border-white bg-foreground shadow"
            style={{ left: `${score}%` }}
          />
        </div>
        <div aria-hidden="true" className="mt-2 flex text-center text-[10px] text-foreground/45">
          {SCALE.map((s) => (
            <span key={s.key} className="min-w-0 truncate px-0.5" style={{ flex: s.to - s.from + 1 }}>
              {VERDICTS[s.key].label}
            </span>
          ))}
        </div>
      </div>

      {reasons.length > 0 && (
        <ul className="flex flex-col gap-1.5" aria-label="このスコアの根拠（PAR.が記録した実際の価格）">
          {reasons.map((r) => (
            <li key={r.text} className="flex items-start gap-2 text-sm text-foreground/80">
              <span
                aria-hidden="true"
                className={`mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full text-[10px] font-bold ${
                  r.good ? "bg-brand text-white" : "bg-foreground/10 text-foreground/50"
                }`}
              >
                {r.good ? "✓" : "−"}
              </span>
              {r.text}
            </li>
          ))}
        </ul>
      )}

      <p className="text-[11px] text-foreground/45">過去の価格との比較です。今後の値動きを保証するものではありません。</p>
    </div>
  );
}
