// The arrow inside shop CTAs (.btn-shop / .btn-ghost, globals.css) - it
// nudges forward on hover so the button feels like it's "going somewhere".
export default function CtaArrow({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg viewBox="0 0 20 20" fill="none" className={`btn-arrow shrink-0 ${className}`} aria-hidden="true">
      <path d="M4 10h11M11 5.5 15.5 10 11 14.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
