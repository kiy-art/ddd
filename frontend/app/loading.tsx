import { ProductGridSkeleton, SkeletonBlock } from "@/components/Skeleton";

// Shown instantly while any page's server data (prices from the backend,
// which can be slow to wake on Render's free plan) is still loading.
export default function Loading() {
  return (
    <div role="status" aria-live="polite" className="mx-auto flex max-w-7xl flex-col gap-10 px-6 py-12 sm:py-16">
      <span className="sr-only">読み込み中…</span>
      <div className="flex flex-col gap-3">
        <SkeletonBlock className="h-3 w-32" />
        <SkeletonBlock className="h-9 w-2/3 max-w-md" />
        <SkeletonBlock className="h-4 w-1/2 max-w-sm" />
      </div>
      <ProductGridSkeleton />
    </div>
  );
}
