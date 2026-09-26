import { VERDICTS, SCORE_NAME, scoreReasons, verdictInfo, verdictMeaning } from "@/lib/buySignal";
import type { ProductDetail } from "@/lib/api";

// "What does this number mean?" - shown under the score ring on the product
// page: the verdict in plain words, the real facts behind today's number,
// and the scale. Only rendered when the score rests on enough real history
// (the same condition under which the ring shows a real score).
export default function ScoreExplanation({ product }: { product: ProductDetail }) {
  const verdict = verdictInfo(product.buy_score);
  const reasons = scoreReasons(product);

  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-border bg-card p-5">
      <p className="text-sm text-foreground">
        {SCORE_NAME} <span className="font-semibold">{product.buy_signal_score}/100</span> は
        <span className="font-semibold">「{verdict.label}」</span>。{verdictMeaning(product)}。
      </p>
      {reasons.length > 0 && (
        <div>
          <p className="text-xs text-foreground/50">このスコアの根拠（PAR.が記録した実際の価格）</p>
          <ul className="mt-1.5 flex flex-col gap-1">
            {reasons.map((r) => (
              <li key={r.text} className="flex items-start gap-2 text-sm text-foreground/80">
                <span
                  aria-hidden="true"
                  className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${r.good ? "bg-signal-high" : "bg-foreground/25"}`}
                />
                {r.text}
              </li>
            ))}
          </ul>
        </div>
      )}
      <p className="text-[11px] leading-relaxed text-foreground/45">
        スコアの目安：
        {(["strong_buy", "buy", "neutral", "not_buy"] as const)
          .map((key) => `${VERDICTS[key].range} ${VERDICTS[key].label}`)
          .join("／")}
        。高いほど買い時です。過去の価格との比較であり、今後の値動きを保証するものではありません。
      </p>
    </div>
  );
}
