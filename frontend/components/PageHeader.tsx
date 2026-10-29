import type { ReactNode } from "react";

import GolfMotif from "@/components/GolfMotif";
import ProductPhotoCollage from "@/components/ProductPhotoCollage";

// The shared light-mode replacement for the old bg-ink (solid black) page
// headers used across category/brand/deals/ranking/etc. Apple-style: an
// off-white/card surface, generous whitespace, real product photography
// (this site's own tracked images) faded into the background instead of a
// flat dark panel, plus a small original line-art accent (see GolfMotif -
// never a photograph, never traced from another site).
const HEADER_TONES = {
  buy: { band: "border-brand/20 bg-mint", pill: "bg-brand text-on-brand", bar: "bg-brand" },
  drop: { band: "border-sale/15 bg-sale-wash", pill: "bg-sale text-white", bar: "bg-sale" },
  gold: { band: "border-gold/20 bg-gold-wash", pill: "bg-gold text-white", bar: "bg-gold" },
  forecast: { band: "border-forecast/15 bg-forecast-wash", pill: "bg-forecast text-white", bar: "bg-forecast" },
  neutral: { band: "border-border bg-card", pill: "bg-accent-dark text-white", bar: "bg-accent" },
} as const;

export default function PageHeader({
  eyebrow,
  title,
  description,
  stats,
  collageImages,
  motif = "fairway",
  tone = "neutral",
  children,
}: {
  eyebrow: string;
  title: ReactNode;
  description?: ReactNode;
  stats?: { label: string; value: ReactNode }[];
  collageImages?: (string | null | undefined)[];
  motif?: "fairway" | "dimples" | "flag";
  // 2026-10-30: same colour roles as the home page sections (SectionHeading):
  // buy = emerald, drop = vermilion, gold = popular, forecast = blue.
  tone?: "buy" | "drop" | "gold" | "forecast" | "neutral";
  children?: ReactNode;
}) {
  const t = HEADER_TONES[tone];
  return (
    <section className={`relative overflow-hidden border-b px-6 py-12 sm:py-20 ${t.band}`}>
      {/* 2026-10-30 (社長室/Webデザイン): the collage slots sit at left 56-88%,
          which on a 375px phone lands on top of the description (e.g. /popular's
          「当サイト独自の順位ではありません」 was covered). Decorative only, so hide it
          below sm. */}
      {collageImages && (
        <div className="hidden sm:block">
          <ProductPhotoCollage images={collageImages} />
        </div>
      )}
      <GolfMotif
        variant={motif}
        className="pointer-events-none absolute -right-16 -top-10 h-56 w-[420px] text-brand/[0.07] sm:h-72 sm:w-[540px]"
      />
      <div className="relative mx-auto max-w-7xl">
        <span className={`inline-block rounded-full px-2.5 py-1 text-[11px] font-bold tracking-wider ${t.pill}`}>
          {eyebrow}
        </span>
        <h1 className="mt-3 flex max-w-4xl gap-3 font-display text-3xl font-bold leading-tight text-foreground sm:text-5xl">
          <span aria-hidden className={`mt-1 w-1.5 shrink-0 self-stretch rounded-full ${t.bar}`} />
          <span>{title}</span>
        </h1>
        {description && (
          <p className="mt-3 max-w-xl text-sm leading-relaxed text-foreground/60 sm:text-base">{description}</p>
        )}
        {stats && stats.length > 0 && (
          <dl className="mt-8 flex flex-wrap gap-x-12 gap-y-6 border-t border-border pt-8">
            {stats.map((s) => (
              <div key={s.label}>
                <dt className="text-xs uppercase tracking-widest text-foreground/45">{s.label}</dt>
                <dd className="font-display text-2xl font-semibold text-foreground sm:text-3xl">{s.value}</dd>
              </div>
            ))}
          </dl>
        )}
        {children}
      </div>
    </section>
  );
}
