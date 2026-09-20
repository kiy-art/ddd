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
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold">今日の買い時ゴルフ用品</h1>
        <p className="mt-1 text-sm text-zinc-500">
          過去30日の価格推移をもとに、値下がり幅が大きい商品から順に表示しています。
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        {FILTER_TABS.map((tab) => (
          <Link
            key={tab}
            href={tab === "all" ? "/" : `/?buy_score=${tab}`}
            className={`rounded-full border px-3 py-1.5 text-xs font-semibold transition-colors ${
              activeTab === tab
                ? "border-zinc-900 bg-zinc-900 text-white dark:border-white dark:bg-white dark:text-zinc-900"
                : "border-zinc-300 text-zinc-600 hover:border-zinc-400 dark:border-zinc-700 dark:text-zinc-300"
            }`}
          >
            {tab === "all" ? "すべて" : BUY_SCORE_LABELS[tab]}
          </Link>
        ))}
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {!error && products.length === 0 && (
        <p className="text-sm text-zinc-500">
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
