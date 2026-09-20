import Image from "next/image";
import Link from "next/link";

import BuyStatusBadge from "@/components/BuyStatusBadge";
import { CATEGORY_LABELS, Product } from "@/lib/api";

function yen(value: number | null): string {
  if (value === null) return "-";
  return `¥${value.toLocaleString("ja-JP")}`;
}

export default function ProductCard({ product }: { product: Product }) {
  return (
    <Link
      href={`/products/${product.slug}`}
      className="flex flex-col overflow-hidden rounded-xl border border-zinc-200 bg-white transition-shadow hover:shadow-md dark:border-zinc-800 dark:bg-zinc-900"
    >
      <div className="relative aspect-square w-full bg-zinc-100 dark:bg-zinc-800">
        {product.image_url ? (
          <Image
            src={product.image_url}
            alt={product.name}
            fill
            unoptimized
            className="object-contain p-4"
          />
        ) : (
          <div className="flex h-full items-center justify-center text-sm text-zinc-400">No Image</div>
        )}
      </div>
      <div className="flex flex-1 flex-col gap-2 p-4">
        <span className="text-xs text-zinc-500">
          {CATEGORY_LABELS[product.category] ?? product.category} ・ {product.brand}
        </span>
        <h3 className="line-clamp-2 font-semibold text-zinc-900 dark:text-zinc-50">{product.name}</h3>
        <div className="mt-auto flex items-end justify-between gap-2">
          <div>
            <div className="text-lg font-bold text-zinc-900 dark:text-zinc-50">
              {yen(product.current_price)}
            </div>
            {product.average_price !== null && (
              <div className="text-xs text-zinc-500">30日平均 {yen(product.average_price)}</div>
            )}
            {product.price_change_percent !== null && (
              <div
                className={`text-xs font-medium ${
                  product.price_change_percent < 0 ? "text-red-600" : "text-zinc-500"
                }`}
              >
                {product.price_change_percent > 0 ? "+" : ""}
                {product.price_change_percent}%
              </div>
            )}
          </div>
          <BuyStatusBadge buyScore={product.buy_score} />
        </div>
        {product.buy_reason && (
          <p className="line-clamp-2 text-xs text-zinc-500">{product.buy_reason}</p>
        )}
      </div>
    </Link>
  );
}
