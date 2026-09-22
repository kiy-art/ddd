"use client";

import { useRouter, useSearchParams } from "next/navigation";

import { removeFromCompare } from "@/lib/compare";

export default function RemoveFromCompareButton({ slug }: { slug: string }) {
  const router = useRouter();
  const searchParams = useSearchParams();

  return (
    <button
      type="button"
      onClick={() => {
        removeFromCompare(slug);
        const remaining = (searchParams.get("slugs") ?? "")
          .split(",")
          .map((s) => s.trim())
          .filter((s) => s && s !== slug);
        router.replace(remaining.length > 0 ? `/compare?slugs=${remaining.map(encodeURIComponent).join(",")}` : "/compare");
      }}
      className="rounded-full border border-border px-3 py-1 text-[11px] font-medium text-foreground/50 transition-colors hover:border-sale/40 hover:text-sale"
    >
      比較から削除
    </button>
  );
}
