import Link from "next/link";

import { BrandCount, brandCategoryHref, categoryHref } from "@/lib/brandFilter";

// STEP64 maker filter, STEP69: each maker is its own page
// (/category/driver/ping) with its own title, so "PING ドライバー" can be
// found in search; "すべて" goes back to the category page.
export default function BrandFilterNav({
  category,
  brands,
  activeBrand,
  totalCount,
  sort,
}: {
  category: string;
  brands: BrandCount[];
  activeBrand: string | null;
  totalCount: number;
  sort: string;
}) {
  if (brands.length < 2 && activeBrand === null) return null;
  const entries: { brand: string | null; count: number }[] = [{ brand: null, count: totalCount }, ...brands];
  return (
    <nav aria-label="メーカーで絞り込む" className="mb-5">
      <span className="text-xs text-foreground/45">メーカー:</span>
      <div className="-mx-6 mt-2 flex gap-2 overflow-x-auto px-6 pb-1 sm:mx-0 sm:flex-wrap sm:overflow-visible sm:px-0">
        {entries.map((entry) => {
          const active = entry.brand === activeBrand;
          return (
            <Link
              key={entry.brand ?? "all"}
              href={entry.brand ? brandCategoryHref(category, entry.brand, sort) : categoryHref(category, { sort })}
              aria-current={active ? "page" : undefined}
              className={`tap shrink-0 whitespace-nowrap rounded-full border px-3.5 py-1.5 text-xs font-semibold transition-colors ${
                active
                  ? "border-brand bg-brand text-on-brand"
                  : "border-border bg-background text-foreground/65 hover:border-brand/40 hover:text-brand"
              }`}
            >
              {entry.brand ?? "すべて"}
              <span className={`ml-1 font-num ${active ? "text-on-brand/80" : "text-foreground/35"}`}>{entry.count}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
