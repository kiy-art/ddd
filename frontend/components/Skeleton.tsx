// Skeleton loading blocks (STEP50). Shapes mirror the real components so
// nothing jumps when data arrives; the shimmer (.skeleton, globals.css) is
// deliberately low-contrast and stops under prefers-reduced-motion.

export function SkeletonBlock({ className = "" }: { className?: string }) {
  return <div aria-hidden="true" className={`skeleton ${className}`} />;
}

// Same footprint as ProductCard: 4:3 photo, eyebrow, 2-line name, score
// ring, then the price row.
export function ProductCardSkeleton() {
  return (
    <div aria-hidden="true" className="flex flex-col overflow-hidden rounded-2xl border border-border bg-card">
      <div className="skeleton aspect-[4/3] w-full rounded-none" />
      <div className="flex flex-1 flex-col gap-4 p-6">
        <div className="flex items-start justify-between gap-3">
          <div className="flex flex-1 flex-col gap-2">
            <SkeletonBlock className="h-3 w-24" />
            <SkeletonBlock className="h-5 w-full" />
            <SkeletonBlock className="h-5 w-2/3" />
          </div>
          <SkeletonBlock className="h-14 w-14 shrink-0 rounded-full" />
        </div>
        <div className="mt-auto flex items-end justify-between border-t border-border pt-4">
          <SkeletonBlock className="h-7 w-28" />
          <SkeletonBlock className="h-6 w-14 rounded-full" />
        </div>
      </div>
    </div>
  );
}

export function ProductGridSkeleton({ count = 6 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: count }, (_, i) => (
        <ProductCardSkeleton key={i} />
      ))}
    </div>
  );
}
