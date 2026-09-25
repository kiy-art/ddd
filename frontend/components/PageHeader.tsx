import type { ReactNode } from "react";

import GolfMotif from "@/components/GolfMotif";
import ProductPhotoCollage from "@/components/ProductPhotoCollage";

// The shared light-mode replacement for the old bg-ink (solid black) page
// headers used across category/brand/deals/ranking/etc. Apple-style: an
// off-white/card surface, generous whitespace, real product photography
// (this site's own tracked images) faded into the background instead of a
// flat dark panel, plus a small original line-art accent (see GolfMotif -
// never a photograph, never traced from another site).
export default function PageHeader({
  eyebrow,
  title,
  description,
  stats,
  collageImages,
  motif = "fairway",
  children,
}: {
  eyebrow: string;
  title: ReactNode;
  description?: ReactNode;
  stats?: { label: string; value: ReactNode }[];
  collageImages?: (string | null | undefined)[];
  motif?: "fairway" | "dimples" | "flag";
  children?: ReactNode;
}) {
  return (
    <section className="relative overflow-hidden border-b border-border bg-card px-6 py-16 sm:py-24">
      {collageImages && <ProductPhotoCollage images={collageImages} />}
      <GolfMotif
        variant={motif}
        className="pointer-events-none absolute -right-16 -top-10 h-56 w-[420px] text-brand/[0.07] sm:h-72 sm:w-[540px]"
      />
      <div className="relative mx-auto max-w-7xl">
        <span className="text-xs font-medium uppercase tracking-[0.3em] text-accent">{eyebrow}</span>
        <h1 className="mt-3 max-w-4xl font-display text-3xl font-semibold leading-tight text-foreground sm:text-5xl">
          {title}
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
