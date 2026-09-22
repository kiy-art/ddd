import type { Metadata } from "next";

import FadeIn from "@/components/FadeIn";
import ProductCard from "@/components/ProductCard";
import { Product, getProducts } from "@/lib/api";

export const revalidate = 0;

function matches(product: Product, query: string): boolean {
  const haystack = `${product.name} ${product.brand} ${product.model_number ?? ""}`.toLowerCase();
  return haystack.includes(query.toLowerCase());
}

export async function generateMetadata({
  searchParams,
}: {
  searchParams: Promise<{ q?: string }>;
}): Promise<Metadata> {
  const { q } = await searchParams;
  return {
    title: q ? `「${q}」の検索結果` : "商品を検索",
    robots: { index: false }, // search results pages add no unique value for crawlers
  };
}

export default async function SearchPage({ searchParams }: { searchParams: Promise<{ q?: string }> }) {
  const { q } = await searchParams;
  const query = (q ?? "").trim();

  let results: Product[] = [];
  let error: string | null = null;
  if (query) {
    try {
      const all = await getProducts({ limit: 200 });
      results = all.filter((p) => matches(p, query));
    } catch {
      error = "商品情報の取得に失敗しました。しばらくしてから再度お試しください。";
    }
  }

  return (
    <div className="mx-auto max-w-7xl px-6 py-16 sm:py-20">
      <form action="/search" method="GET" className="flex max-w-xl gap-2">
        <input
          type="text"
          name="q"
          defaultValue={query}
          placeholder="商品名・ブランドで検索（例: G440, Titleist）"
          className="flex-1 rounded-full border border-border bg-card px-5 py-3 text-sm text-foreground outline-none focus:border-brand"
        />
        <button
          type="submit"
          className="rounded-full bg-brand px-6 py-3 text-sm font-semibold text-white hover:opacity-90"
        >
          検索
        </button>
      </form>

      <div className="mt-10">
        {!query && <p className="text-sm text-foreground/50">商品名やブランド名を入力して検索してください。</p>}

        {query && error && <p className="text-sm text-red-600">{error}</p>}

        {query && !error && (
          <>
            <p className="text-sm text-foreground/50">
              「{query}」の検索結果: {results.length}件
            </p>
            {results.length === 0 ? (
              <p className="mt-8 rounded-2xl border border-dashed border-border bg-card px-4 py-16 text-center text-sm text-foreground/50">
                該当する商品が見つかりませんでした。別のキーワードでお試しください。
              </p>
            ) : (
              <div className="mt-8 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
                {results.map((product, i) => (
                  <FadeIn key={product.id} delay={(i % 6) * 60}>
                    <ProductCard product={product} listSource="search" />
                  </FadeIn>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
