import Image from "next/image";
import Link from "next/link";

import BuyStatusBadge from "@/components/BuyStatusBadge";
import { CATEGORY_LABELS, Product } from "@/lib/api";

function yen(value: number | null): string {
  if (value === null) return "-";
  return `¥${value.toLocaleString("ja-JP")}`;
}

export default function ProductCard({ product }: { product: Product }) {
  const isDiscounted = (product.price_change_percent ?? 0) < 0;

  return (
    <Link
      href={`/products/${product.slug}`}
      className="group flex flex-col overflow-hidden rounded-xl border border-border bg-card transition-all hover:-translate-y-0.5 hover:shadow-lg"
    >
      <div className="relative aspect-square w-full bg-background">
        {product.image_url ? (
          <Image
            src={product.image_url}
            alt={product.name}
            fill
            unoptimized
            className="object-contain p-4 transition-transform duration-200 group-hover:scale-105"
          />
        ) : (
          <div className="flex h-full items-center justify-center text-sm text-foreground/30">No Image</div>
        )}
        {isDiscounted && (
          <span className="absolute left-2 top-2 rounded-full bg-accent px-2.5 py-1 text-xs font-bold text-white shadow-sm">
            {product.price_change_percent}%
          </span>
        )}
      </div>
      <div className="flex flex-1 flex-col gap-2 p-4">
        <span className="text-xs font-medium text-foreground/50">
          {CATEGORY_LABELS[product.category] ?? product.category} ・ {product.brand}
        </span>
        <h3 className="line-clamp-2 font-semibold text-foreground">{product.name}</h3>
        <div className="mt-auto flex items-end justify-between gap-2">
          <div>
            <div className="text-lg font-bold text-foreground">{yen(product.current_price)}</div>
            {product.average_price !== null && (
              <div className="text-xs text-foreground/50">30日平均 {yen(product.average_price)}</div>
            )}
          </div>
          <BuyStatusBadge buyScore={product.buy_score} />
        </div>
        {product.buy_reason && (
          <p className="line-clamp-2 text-xs text-foreground/50">{product.buy_reason}</p>
        )}
      </div>
    </Link>
  );
}
