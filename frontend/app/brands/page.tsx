import type { Metadata } from "next";
import Link from "next/link";

import FadeIn from "@/components/FadeIn";
import { getBrands } from "@/lib/api";

export const revalidate = 0;

export const metadata: Metadata = {
  title: "ブランド一覧",
  description: "取り扱いゴルフブランドの一覧です。メーカーごとに商品の価格推移と買い時判定を確認できます。",
};

export default async function BrandsPage() {
  const brands = await getBrands();

  return (
    <div>
      <section className="bg-foreground px-6 py-20 text-white sm:py-28">
        <div className="mx-auto max-w-7xl">
          <span className="text-xs font-medium uppercase tracking-[0.3em] text-accent">Brands</span>
          <h1 className="mt-3 font-display text-4xl font-semibold leading-tight sm:text-5xl">ブランドで探す</h1>
          <p className="mt-3 text-sm text-white/70">{brands.length}ブランドの価格を分析中</p>
        </div>
      </section>

      <section className="px-6 py-16 sm:py-20">
        <div className="mx-auto max-w-7xl">
          {brands.length === 0 ? (
            <p className="rounded-2xl border border-dashed border-border bg-card px-4 py-16 text-center text-sm text-foreground/50">
              現在表示できるブランドがありません。
            </p>
          ) : (
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
              {brands.map((b, i) => (
                <FadeIn key={b.brand} delay={(i % 8) * 50}>
                  <Link
                    href={`/brand/${encodeURIComponent(b.brand)}`}
                    className="flex flex-col gap-1 rounded-2xl border border-border bg-card p-6 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-[0_24px_48px_-24px_rgba(20,19,15,0.22)]"
                  >
                    <span className="font-display text-lg font-medium text-foreground">{b.brand}</span>
                    <span className="text-xs text-foreground/45">{b.product_count}商品</span>
                  </Link>
                </FadeIn>
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
