"use client";

import { useCallback, useSyncExternalStore } from "react";

import { MAX_COMPARE, getCompareList, isInCompare, subscribe, toggleCompare } from "@/lib/compare";

const getServerSnapshot = () => false;
const getServerCount = () => 0;

export default function CompareButton({ slug, className }: { slug: string; className?: string }) {
  const getSnapshot = useCallback(() => isInCompare(slug), [slug]);
  const inCompare = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
  const getCount = useCallback(() => getCompareList().length, []);
  const count = useSyncExternalStore(subscribe, getCount, getServerCount);
  const atLimit = !inCompare && count >= MAX_COMPARE;

  return (
    <button
      type="button"
      disabled={atLimit}
      onClick={(e) => {
        e.preventDefault();
        e.stopPropagation();
        toggleCompare(slug);
      }}
      aria-pressed={inCompare}
      title={atLimit ? `比較は最大${MAX_COMPARE}件までです` : undefined}
      className={
        className ??
        `rounded-full border px-3 py-1.5 text-[11px] font-semibold transition-colors ${
          inCompare
            ? "border-brand bg-brand text-on-brand"
            : "border-border bg-background text-foreground/60 hover:border-brand/40 hover:text-brand"
        } disabled:cursor-not-allowed disabled:opacity-40`
      }
    >
      {inCompare ? "✓ 比較中" : "＋ 比較"}
    </button>
  );
}
