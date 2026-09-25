import type { Metadata } from "next";
import Link from "next/link";

import FadeIn from "@/components/FadeIn";
import PageHeader from "@/components/PageHeader";
import ProductCard from "@/components/ProductCard";
import { CATEGORIES, CATEGORY_LABELS, Product, getCategoryProducts } from "@/lib/api";

export const revalidate = 0;

export const metadata: Metadata = {
  title: "クラブ診断",
  description: "カテゴリと予算から、今チェックすべきゴルフ用品を絞り込めます。",
  robots: { index: false }, // a filtered results page, same as /search - no unique content to index
};

const BUDGET_OPTIONS = [
  { value: "", label: "指定しない" },
  { value: "low", label: "〜3万円" },
  { value: "mid", label: "3万〜7万円" },
  { value: "high", label: "7万〜15万円" },
  { value: "premium", label: "15万円〜" },
] as const;

const BUDGET_RANGES: Record<string, [number, number]> = {
  low: [0, 30000],
  mid: [30000, 70000],
  high: [70000, 150000],
  premium: [150000, Infinity],
};

const PRIORITY_OPTIONS = [
  { value: "buy_now", label: "今の買い時度で選ぶ" },
  { value: "cheap", label: "とにかく安い順で選ぶ" },
  { value: "discount", label: "値下がり幅が大きい順で選ぶ" },
] as const;

type Priority = (typeof PRIORITY_OPTIONS)[number]["value"];

function isPriority(value: string | undefined): value is Priority {
  return !!value && PRIORITY_OPTIONS.some((o) => o.value === value);
}

function sortByPriority(products: Product[], priority: Priority): Product[] {
  const list = [...products];
  if (priority === "cheap") {
    return list.sort((a, b) => (a.current_price ?? Infinity) - (b.current_price ?? Infinity));
  }
  if (priority === "discount") {
    return list.sort((a, b) => (a.price_change_percent ?? 0) - (b.price_change_percent ?? 0));
  }
  return list.sort((a, b) => (b.buy_signal_score ?? -1) - (a.buy_signal_score ?? -1));
}

export default async function FinderPage({
  searchParams,
}: {
  searchParams: Promise<{ category?: string; budget?: string; priority?: string }>;
}) {
  const { category, budget, priority: priorityParam } = await searchParams;
  const priority: Priority = isPriority(priorityParam) ? priorityParam : "buy_now";
  const validCategory = CATEGORIES.includes(category as (typeof CATEGORIES)[number]) ? category : undefined;

  let results: Product[] = [];
  let error: string | null = null;
  if (validCategory) {
    try {
      const all = await getCategoryProducts(validCategory);
      const range = budget ? BUDGET_RANGES[budget] : undefined;
      const filtered = range
        ? all.filter((p) => p.current_price !== null && p.current_price >= range[0] && p.current_price < range[1])
        : all;
      results = sortByPriority(filtered, priority).slice(0, 6);
    } catch {
      error = "商品情報の取得に失敗しました。しばらくしてから再度お試しください。";
    }
  }

  return (
    <div>
      <PageHeader
        eyebrow="Golf Club Finder"
        title="クラブ診断"
        description="カテゴリと予算を選ぶだけで、今チェックすべき商品を価格データから絞り込みます。"
        motif="flag"
      />

      <section className="px-6 py-12 sm:py-16">
        <div className="mx-auto max-w-4xl">
          <form action="/finder" method="GET" className="flex flex-col gap-8 rounded-2xl border border-border bg-card p-6 sm:p-8">
            <div>
              <span className="text-xs font-medium uppercase tracking-widest text-foreground/40">
                1. カテゴリを選ぶ
              </span>
              <div className="mt-3 flex flex-wrap gap-2">
                {CATEGORIES.map((c) => (
                  <label key={c} className="cursor-pointer">
                    <input
                      type="radio"
                      name="category"
                      value={c}
                      defaultChecked={validCategory === c}
                      className="peer sr-only"
                    />
                    <span className="block rounded-full border border-border px-4 py-2 text-sm font-medium text-foreground/60 transition-colors peer-checked:border-brand peer-checked:bg-brand peer-checked:text-white hover:border-brand/40">
                      {CATEGORY_LABELS[c]}
                    </span>
                  </label>
                ))}
              </div>
            </div>

            <div>
              <span className="text-xs font-medium uppercase tracking-widest text-foreground/40">
                2. 予算を選ぶ
              </span>
              <div className="mt-3 flex flex-wrap gap-2">
                {BUDGET_OPTIONS.map((b) => (
                  <label key={b.value} className="cursor-pointer">
                    <input
                      type="radio"
                      name="budget"
                      value={b.value}
                      defaultChecked={(budget ?? "") === b.value}
                      className="peer sr-only"
                    />
                    <span className="block rounded-full border border-border px-4 py-2 text-sm font-medium text-foreground/60 transition-colors peer-checked:border-brand peer-checked:bg-brand peer-checked:text-white hover:border-brand/40">
                      {b.label}
                    </span>
                  </label>
                ))}
              </div>
            </div>

            <div>
              <span className="text-xs font-medium uppercase tracking-widest text-foreground/40">
                3. 重視するポイント
              </span>
              <div className="mt-3 flex flex-wrap gap-2">
                {PRIORITY_OPTIONS.map((p) => (
                  <label key={p.value} className="cursor-pointer">
                    <input
                      type="radio"
                      name="priority"
                      value={p.value}
                      defaultChecked={priority === p.value}
                      className="peer sr-only"
                    />
                    <span className="block rounded-full border border-border px-4 py-2 text-sm font-medium text-foreground/60 transition-colors peer-checked:border-brand peer-checked:bg-brand peer-checked:text-white hover:border-brand/40">
                      {p.label}
                    </span>
                  </label>
                ))}
              </div>
            </div>

            <button
              type="submit"
              className="w-fit rounded-full bg-brand px-8 py-3.5 text-sm font-semibold text-white transition-transform hover:scale-[1.02]"
            >
              診断する
            </button>
          </form>

          <div className="mt-12">
            {!validCategory && !error && (
              <p className="text-sm text-foreground/50">カテゴリを選んで「診断する」を押してください。</p>
            )}

            {error && <p className="text-sm text-red-600">{error}</p>}

            {validCategory && !error && (
              <>
                <div className="flex items-center justify-between">
                  <p className="text-sm text-foreground/50">
                    {CATEGORY_LABELS[validCategory]}
                    {budget && ` ・ ${BUDGET_OPTIONS.find((b) => b.value === budget)?.label}`} の診断結果:{" "}
                    {results.length}件
                  </p>
                  <Link href={`/category/${validCategory}`} className="text-xs font-semibold text-brand hover:underline">
                    カテゴリ全体を見る →
                  </Link>
                </div>

                {results.length === 0 ? (
                  <p className="mt-8 rounded-2xl border border-dashed border-border bg-card px-4 py-16 text-center text-sm text-foreground/50">
                    条件に合う商品が見つかりませんでした。予算を変えてお試しください。
                  </p>
                ) : (
                  <div className="mt-8 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
                    {results.map((product, i) => (
                      <FadeIn key={product.id} delay={(i % 6) * 60}>
                        <ProductCard product={product} listSource="finder" />
                      </FadeIn>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
