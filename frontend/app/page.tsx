import ProductCard from "@/components/ProductCard";
import { getProducts } from "@/lib/api";

export const revalidate = 0;

export default async function Home() {
  let products = [] as Awaited<ReturnType<typeof getProducts>>;
  let error: string | null = null;
  try {
    products = await getProducts();
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

      {error && <p className="text-sm text-red-600">{error}</p>}

      {!error && products.length === 0 && (
        <p className="text-sm text-zinc-500">現在表示できる商品がありません。価格データが蓄積され次第表示されます。</p>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {products.map((product) => (
          <ProductCard key={product.id} product={product} />
        ))}
      </div>
    </div>
  );
}
