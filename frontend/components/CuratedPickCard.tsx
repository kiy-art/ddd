"use client";

import Link from "next/link";

import SafeProductImage from "@/components/SafeProductImage";
import { Product } from "@/lib/api";
import { trackEvent } from "@/lib/analytics";

function yen(value: number | null): string {
  if (value === null) return "-";
  return `¥${value.toLocaleString("ja-JP")}`;
}

export default function CuratedPickCard({
  label,
  product,
  listSource,
}: {
  label: string;
  product: Product;
  listSource: string;
}) {
  return (
    <Link
      href={`/products/${product.slug}`}
      onClick={() =>
        trackEvent("product_card_click", { product_id: product.id, product_slug: product.slug, list_source: listSource })
      }
      className="card-lux group flex flex-col gap-3 rounded-2xl p-4"
    >
      <span className="inline-flex w-fit items-center gap-1.5 rounded-full bg-background px-3 py-1 text-[11px] font-semibold text-foreground/70">
        {label}
      </span>
      <div className="relative aspect-[4/3] w-full overflow-hidden rounded-xl bg-background">
        <SafeProductImage
            src={product.image_url}
            alt={product.name}
            category={product.category}
            className="object-contain p-4 transition-transform duration-300 group-hover:scale-[1.04]"
          />
      </div>
      <div>
        <span className="text-[10px] font-medium uppercase tracking-widest text-foreground/40">{product.brand}</span>
        <h3 className="mt-0.5 line-clamp-2 text-sm font-medium leading-snug text-foreground">{product.name}</h3>
        <p className="mt-1 font-num text-lg font-semibold text-foreground">{yen(product.current_price)}</p>
      </div>
    </Link>
  );
}
