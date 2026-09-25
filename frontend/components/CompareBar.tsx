"use client";

import Link from "next/link";
import { useSyncExternalStore } from "react";

import { clearCompare, getCompareList, subscribe } from "@/lib/compare";

const EMPTY: string[] = [];
const getServerSnapshot = (): string[] => EMPTY;

export default function CompareBar() {
  const slugs = useSyncExternalStore(subscribe, getCompareList, getServerSnapshot);

  if (slugs.length < 2) return null;

  return (
    <div className="fixed inset-x-0 bottom-16 z-40 border-t border-border bg-card/95 px-4 py-3 backdrop-blur-sm sm:px-6 md:bottom-0">
      <div className="mx-auto flex max-w-5xl items-center justify-between gap-4">
        <div className="min-w-0">
          <span className="text-xs font-medium uppercase tracking-widest text-foreground/40">Compare</span>
          <p className="truncate text-sm font-medium text-foreground">{slugs.length}商品を比較リストに追加中</p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <button
            type="button"
            onClick={() => clearCompare()}
            className="rounded-full px-3 py-2 text-xs font-medium text-foreground/50 hover:text-foreground"
          >
            クリア
          </button>
          <Link
            href={`/compare?slugs=${slugs.map(encodeURIComponent).join(",")}`}
            className="rounded-full bg-brand px-5 py-2.5 text-sm font-semibold text-white transition-transform hover:scale-[1.03]"
          >
            比較する ({slugs.length})
          </Link>
        </div>
      </div>
    </div>
  );
}
