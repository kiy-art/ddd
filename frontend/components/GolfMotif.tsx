// Original, hand-drawn line-art motifs (fairway contour lines / a flag on a
// green / a dimple grid) in the same thin-stroke language as CategoryIcon
// and Hero's existing arc motif - never a photograph or a traced/copied
// image. Used as a subtle decorative accent, not the page's main visual.
const VARIANTS: Record<string, React.ReactNode> = {
  fairway: (
    <>
      <path d="M-10 120 C 60 80, 140 140, 220 90 S 380 60, 460 110" strokeLinecap="round" />
      <path d="M-10 160 C 70 130, 150 175, 230 135 S 390 110, 460 155" strokeLinecap="round" opacity="0.6" />
      <path d="M-10 200 C 80 180, 160 210, 240 185 S 400 165, 460 200" strokeLinecap="round" opacity="0.35" />
      <circle cx="330" cy="70" r="5" fill="currentColor" stroke="none" />
      <path d="M330 70 L330 20" strokeLinecap="round" />
      <path d="M330 20 L358 30 L330 40 Z" fill="currentColor" strokeLinecap="round" strokeLinejoin="round" />
    </>
  ),
  dimples: (
    <>
      {Array.from({ length: 6 }).map((_, row) =>
        Array.from({ length: 8 }).map((__, col) => (
          <circle
            key={`${row}-${col}`}
            cx={20 + col * 32 + (row % 2 === 0 ? 0 : 16)}
            cy={20 + row * 32}
            r="3"
            fill="currentColor"
            stroke="none"
            opacity={0.5 - row * 0.05}
          />
        ))
      )}
    </>
  ),
  flag: (
    <>
      <circle cx="100" cy="150" r="70" opacity="0.4" />
      <circle cx="100" cy="150" r="2.5" fill="currentColor" stroke="none" />
      <path d="M100 150 L100 30" strokeLinecap="round" />
      <path d="M100 30 L145 45 L100 60 Z" fill="currentColor" strokeLinecap="round" strokeLinejoin="round" />
    </>
  ),
};

export default function GolfMotif({
  variant = "fairway",
  className,
}: {
  variant?: keyof typeof VARIANTS;
  className?: string;
}) {
  return (
    <svg
      viewBox="0 0 460 220"
      className={className}
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      aria-hidden="true"
    >
      {VARIANTS[variant] ?? VARIANTS.fairway}
    </svg>
  );
}
