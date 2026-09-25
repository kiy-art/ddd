"use client";

import Link from "next/link";

import CategoryIcon from "@/components/CategoryIcon";
import SafeProductImage from "@/components/SafeProductImage";
import { Product } from "@/lib/api";
import { trackEvent } from "@/lib/analytics";

function yen(value: number | null): string {
  if (value === null) return "-";
  return `¥${value.toLocaleString("ja-JP")}`;
}

export default function CuratedPickCard({
  icon,
  label,
  product,
  listSource,
}: {
  icon: string;
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
      className="group flex flex-col gap-3 rounded-2xl border border-border bg-card p-4 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-[0_20px_40px_-20px_rgba(20,19,15,0.2)]"
    >
      <span className="inline-flex w-fit items-center gap-1.5 rounded-full bg-background px-3 py-1 text-[11px] font-semibold text-foreground/70">
        {icon} {label}
      </span>
      <div className="relative aspect-[4/3] w-full overflow-hidden rounded-xl bg-background">
        {product.image_url ? (
          <SafeProductImage
            src={product.image_url}
            alt={product.name}
            category={product.category}
            className="object-contain p-4 transition-transform duration-300 group-hover:scale-[1.04]"
          />
        ) : (
          <CategoryIcon category={product.category} />
        )}
      </div>
      <div>
        <span className="text-[10px] font-medium uppercase tracking-widest text-foreground/40">{product.brand}</span>
        <h3 className="mt-0.5 line-clamp-2 text-sm font-medium leading-snug text-foreground">{product.name}</h3>
        <p className="mt-1 font-display text-lg font-semibold text-foreground">{yen(product.current_price)}</p>
      </div>
    </Link>
  );
}
