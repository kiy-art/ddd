// Section heading with a colour role, so visitors can tell at a glance what
// each band of the page is about (2026-10-30, "白一色で着目点がわからない").
// buy = emerald, drop = vermilion, gold = popular/top, forecast = blue,
// neutral = slate, onDark = for the deep-green ranking band.
export type SectionTone = "buy" | "drop" | "gold" | "forecast" | "neutral" | "onDark";

const TONES: Record<SectionTone, { pill: string; bar: string; title: string; sub: string }> = {
  buy: { pill: "bg-brand text-on-brand", bar: "bg-brand", title: "text-foreground", sub: "text-foreground/65" },
  drop: { pill: "bg-sale text-white", bar: "bg-sale", title: "text-foreground", sub: "text-foreground/65" },
  gold: { pill: "bg-gold text-white", bar: "bg-gold", title: "text-foreground", sub: "text-foreground/65" },
  forecast: { pill: "bg-forecast text-white", bar: "bg-forecast", title: "text-foreground", sub: "text-foreground/65" },
  neutral: { pill: "bg-accent-dark text-white", bar: "bg-accent", title: "text-foreground", sub: "text-foreground/65" },
  onDark: { pill: "bg-[#fbbf24] text-fairway", bar: "bg-[#fbbf24]", title: "text-white", sub: "text-white/75" },
};

export default function SectionHeading({
  tone,
  label,
  title,
  sub,
}: {
  tone: SectionTone;
  label: string;
  title: string;
  sub?: string;
}) {
  const t = TONES[tone];
  return (
    <div className="flex gap-3">
      <span aria-hidden className={`mt-1 w-1.5 shrink-0 rounded-full ${t.bar}`} />
      <div>
        <span className={`inline-block rounded-full px-2.5 py-1 text-[11px] font-bold tracking-wider ${t.pill}`}>
          {label}
        </span>
        <h2 className={`mt-2 font-display text-2xl font-bold leading-tight sm:text-4xl ${t.title}`}>{title}</h2>
        {sub && <p className={`mt-2 max-w-lg text-sm ${t.sub}`}>{sub}</p>}
      </div>
    </div>
  );
}
