"use client";

import { useEffect, useState } from "react";

import FadeIn from "@/components/FadeIn";
import ProductCard from "@/components/ProductCard";
import { Product, getProduct } from "@/lib/api";
import { getFavorites } from "@/lib/favorites";
import { getRecentlyViewed } from "@/lib/recentlyViewed";

async function loadProducts(slugs: string[]): Promise<Product[]> {
  const results = await Promise.all(
    slugs.map((slug) =>
      getProduct(slug)
        .then((p) => p as Product)
        .catch(() => null)
    )
  );
  return results.filter((p): p is Product => p !== null);
}

function ProductGrid({ products, listSource }: { products: Product[]; listSource: string }) {
  return (
    <div className="mt-6 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
      {products.map((product, i) => (
        <FadeIn key={product.id} delay={(i % 6) * 60}>
          <ProductCard product={product} listSource={listSource} />
        </FadeIn>
      ))}
    </div>
  );
}

export default function FavoritesClient() {
  const [favorites, setFavorites] = useState<Product[] | null>(null);
  const [recentlyViewed, setRecentlyViewed] = useState<Product[] | null>(null);

  useEffect(() => {
    loadProducts(getFavorites()).then(setFavorites);
    loadProducts(getRecentlyViewed()).then(setRecentlyViewed);
  }, []);

  return (
    <div className="mx-auto max-w-7xl px-6 py-16 sm:py-20">
      <p className="text-xs font-medium uppercase tracking-[0.3em] text-accent">My Page</p>
      <h1 className="mt-2 font-display text-3xl font-semibold text-foreground">お気に入り</h1>
      <p className="mt-2 text-sm text-foreground/50">
        この端末のブラウザにのみ保存されます。他の端末やブラウザとは共有されません。
      </p>

      {favorites === null && <p className="mt-8 text-sm text-foreground/50">読み込み中...</p>}
      {favorites !== null && favorites.length === 0 && (
        <p className="mt-8 rounded-2xl border border-dashed border-border bg-card px-4 py-12 text-center text-sm text-foreground/50">
          お気に入り登録した商品はまだありません。商品カードのハートアイコンから追加できます。
        </p>
      )}
      {favorites !== null && favorites.length > 0 && (
        <ProductGrid products={favorites} listSource="favorites" />
      )}

      <div className="mt-16 border-t border-border pt-10">
        <h2 className="font-display text-xl font-semibold text-foreground">最近見た商品</h2>
        {recentlyViewed !== null && recentlyViewed.length === 0 && (
          <p className="mt-4 text-sm text-foreground/50">まだ商品ページを見ていません。</p>
        )}
        {recentlyViewed !== null && recentlyViewed.length > 0 && (
          <ProductGrid products={recentlyViewed} listSource="recently_viewed" />
        )}
      </div>
    </div>
  );
}
