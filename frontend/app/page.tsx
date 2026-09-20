import Link from "next/link";

import ProductCard from "@/components/ProductCard";
import { BUY_SCORE_LABELS, getProducts } from "@/lib/api";

export const revalidate = 0;

const FILTER_TABS = ["all", "strong_buy", "buy", "neutral", "not_buy"] as const;
type FilterTab = (typeof FILTER_TABS)[number];

function isFilterTab(value: string | undefined): value is FilterTab {
  return !!value && (FILTER_TABS as readonly string[]).includes(value);
}

export default async function Home({
  searchParams,
}: {
  searchParams: Promise<{ buy_score?: string }>;
}) {
  const params = await searchParams;
  const activeTab: FilterTab = isFilterTab(params.buy_score) ? params.buy_score : "all";

  let products = [] as Awaited<ReturnType<typeof getProducts>>;
  let error: string | null = null;
  try {
    products = await getProducts(activeTab === "all" ? undefined : { buy_score: activeTab });
  } catch {
    error = "商品情報の取得に失敗しました。しばらくしてから再度お試しください。";
  }

  return (
    <div className="flex flex-col gap-8">
      <section className="overflow-hidden rounded-2xl bg-gradient-to-br from-brand to-brand-dark px-6 py-10 text-white sm:px-10 sm:py-14">
        <p className="text-xs font-semibold uppercase tracking-widest text-accent">Today&apos;s Deals</p>
        <h1 className="mt-2 text-3xl font-bold sm:text-4xl">今日の買い時ゴルフ用品</h1>
        <p className="mt-3 max-w-xl text-sm text-white/80 sm:text-base">
          過去30日の価格推移をAIとルールベース分析で判定し、値下がり幅が大きい商品から順に紹介しています。
        </p>
      </section>

      <div className="flex flex-wrap gap-2">
        {FILTER_TABS.map((tab) => (
          <Link
            key={tab}
            href={tab === "all" ? "/" : `/?buy_score=${tab}`}
            className={`rounded-full border px-3.5 py-1.5 text-xs font-semibold transition-colors ${
              activeTab === tab
                ? "border-brand bg-brand text-white"
                : "border-border bg-card text-foreground/60 hover:border-brand/40 hover:text-brand dark:hover:text-brand-light"
            }`}
          >
            {tab === "all" ? "すべて" : BUY_SCORE_LABELS[tab]}
          </Link>
        ))}
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {!error && products.length === 0 && (
        <p className="rounded-xl border border-dashed border-border bg-card px-4 py-8 text-center text-sm text-foreground/50">
          現在表示できる商品がありません。価格データが蓄積され次第表示されます。
        </p>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {products.map((product) => (
          <ProductCard key={product.id} product={product} />
        ))}
      </div>
    </div>
  );
}
