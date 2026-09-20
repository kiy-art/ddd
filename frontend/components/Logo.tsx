export function LogoMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" fill="none" className={className} aria-hidden="true">
      <circle cx="16" cy="16" r="13.5" stroke="currentColor" strokeWidth="2" opacity="0.25" />
      <path
        d="M16 2.5 A13.5 13.5 0 0 1 27.8 22"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
      <circle cx="27.8" cy="22" r="2.4" fill="currentColor" />
    </svg>
  );
}

export default function Logo({ className }: { className?: string }) {
  return (
    <span className={`inline-flex items-center gap-2 ${className ?? ""}`}>
      <LogoMark className="h-6 w-6 text-current" />
      <span className="font-display text-xl font-semibold tracking-tight">PAR.</span>
    </span>
  );
}
