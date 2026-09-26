import { SkeletonBlock } from "@/components/Skeleton";

// Product page skeleton: photo | name, score ring + price, verdict, chart -
// the same two-column layout as the real page, so nothing shifts on load.
export default function Loading() {
  return (
    <div role="status" aria-live="polite" className="mx-auto max-w-7xl px-6 py-12 sm:py-16">
      <span className="sr-only">商品情報を読み込み中…</span>
      <div className="grid grid-cols-1 gap-12 lg:grid-cols-2 lg:gap-16">
        <SkeletonBlock className="aspect-square w-full rounded-2xl" />
        <div className="flex flex-col gap-6">
          <div className="flex flex-col gap-3">
            <SkeletonBlock className="h-3 w-28" />
            <SkeletonBlock className="h-9 w-full" />
            <SkeletonBlock className="h-9 w-3/4" />
          </div>
          <div className="flex items-center gap-6 rounded-2xl border border-border bg-card p-6">
            <SkeletonBlock className="h-[108px] w-[108px] shrink-0 rounded-full" />
            <div className="flex flex-1 flex-col gap-3 border-l border-border pl-6">
              <SkeletonBlock className="h-3 w-16" />
              <SkeletonBlock className="h-10 w-40" />
              <SkeletonBlock className="h-4 w-24" />
            </div>
          </div>
          <SkeletonBlock className="h-28 w-full rounded-2xl" />
          <div className="rounded-2xl border border-border bg-card p-6">
            <SkeletonBlock className="mb-4 h-7 w-56 rounded-full" />
            <SkeletonBlock className="h-48 w-full" />
          </div>
        </div>
      </div>
    </div>
  );
}
