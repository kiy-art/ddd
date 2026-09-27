import type { Product } from "@/lib/api";
import { getPositioningFacts } from "@/lib/badges";
import { describeProduct, specRows } from "@/lib/productSpecs";

// STEP61 "商品の特徴": what the product is, before the price talk - built
// only from stored facts (lib/productSpecs.ts describeProduct) and the
// seller-stated specs parsed from the matched Rakuten listing. When no
// spec is stored yet, it says where to check instead of guessing.
export default function ProductOverview({ product, className = "" }: { product: Product; className?: string }) {
  const lines = describeProduct(product);
  const facts = getPositioningFacts(product);
  const specs = specRows(product);

  return (
    <section aria-labelledby="product-overview" className={`card-lux rounded-2xl p-5 sm:p-6 ${className}`}>
      <span className="text-xs font-medium uppercase tracking-[0.3em] text-accent">About</span>
      <h2 id="product-overview" className="mt-1 font-display text-lg font-semibold text-foreground">
        商品の特徴
      </h2>
      <div className="mt-3 flex flex-col gap-1 text-sm leading-relaxed text-foreground/70">
        {lines.map((line) => (
          <p key={line}>{line}</p>
        ))}
      </div>

      {facts.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {facts.map((fact) => (
            <span
              key={fact.label}
              className="rounded-full border border-brand/25 bg-mint px-3 py-1 text-xs font-semibold text-brand"
            >
              {fact.label}
            </span>
          ))}
        </div>
      )}

      {specs.length > 0 ? (
        <div className="mt-5">
          <h3 className="text-xs font-semibold text-foreground/50">スペック（販売ページ記載）</h3>
          <dl className="mt-2 grid grid-cols-1 gap-x-6 sm:grid-cols-2">
            {specs.map((s) => (
              <div key={s.key} className="flex items-baseline justify-between gap-3 border-b border-border py-2 text-sm">
                <dt className="shrink-0 text-foreground/50">{s.label}</dt>
                <dd className="text-right font-medium text-foreground">{s.value}</dd>
              </div>
            ))}
          </dl>
          <p className="mt-2 text-[11px] leading-relaxed text-foreground/40">
            楽天市場の販売ページに記載されたスペックです。ロフトやシャフトなどは購入時に選べる場合があるため、購入前に販売ページでご確認ください。
          </p>
        </div>
      ) : (
        <p className="mt-4 text-xs text-foreground/45">
          ロフト角・シャフトなどの詳しいスペックは、各販売ページでご確認ください（取得でき次第ここに表示します）。
        </p>
      )}
    </section>
  );
}
