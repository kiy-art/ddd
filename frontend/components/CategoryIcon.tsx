const ICONS: Record<string, React.ReactNode> = {
  driver: (
    <>
      <path d="M24 70 L62 30" strokeLinecap="round" />
      <path
        d="M62 30 C70 22 82 22 88 30 C94 38 92 50 82 56 C72 62 58 58 54 48 C51 41 55 34 62 30 Z"
        strokeLinejoin="round"
      />
    </>
  ),
  iron: (
    <>
      <path d="M28 72 L58 26" strokeLinecap="round" />
      <path d="M58 26 L86 34 L74 58 L52 50 Z" strokeLinejoin="round" />
      <path d="M60 34 L78 40" strokeLinecap="round" opacity="0.5" />
      <path d="M57 41 L75 47" strokeLinecap="round" opacity="0.5" />
    </>
  ),
  wedge: (
    <>
      <path d="M28 72 L56 28" strokeLinecap="round" />
      <path d="M56 28 L88 30 L80 56 L52 52 Z" strokeLinejoin="round" />
      <path d="M58 36 L80 38" strokeLinecap="round" opacity="0.5" />
      <path d="M56 43 L78 45" strokeLinecap="round" opacity="0.5" />
      <path d="M55 50 L77 51" strokeLinecap="round" opacity="0.5" />
    </>
  ),
  putter: (
    <>
      <path d="M40 74 L52 30" strokeLinecap="round" />
      <rect x="44" y="24" width="34" height="14" rx="2" transform="rotate(-8 44 24)" />
    </>
  ),
  ball: (
    <>
      <circle cx="56" cy="52" r="26" />
      <circle cx="47" cy="43" r="1.6" fill="currentColor" stroke="none" />
      <circle cx="58" cy="40" r="1.6" fill="currentColor" stroke="none" />
      <circle cx="68" cy="46" r="1.6" fill="currentColor" stroke="none" />
      <circle cx="43" cy="55" r="1.6" fill="currentColor" stroke="none" />
      <circle cx="55" cy="56" r="1.6" fill="currentColor" stroke="none" />
      <circle cx="67" cy="59" r="1.6" fill="currentColor" stroke="none" />
      <circle cx="48" cy="66" r="1.6" fill="currentColor" stroke="none" />
      <circle cx="61" cy="68" r="1.6" fill="currentColor" stroke="none" />
    </>
  ),
};

export default function CategoryIcon({ category, className }: { category: string; className?: string }) {
  const icon = ICONS[category] ?? ICONS.ball;
  return (
    <div className={`flex h-full w-full items-center justify-center ${className ?? ""}`}>
      <svg
        viewBox="0 0 112 96"
        className="h-2/3 w-2/3 text-foreground/25"
        fill="none"
        stroke="currentColor"
        strokeWidth={3}
      >
        {icon}
      </svg>
    </div>
  );
}
