import PrNotice from "@/components/PrNotice";
import TrackedCta from "@/components/TrackedCta";
import { Product } from "@/lib/api";
import { displayName } from "@/lib/displayName";
import { shopOf } from "@/lib/shopRows";

/**
 * Guide pages: shop entrance for readers who finished the article. The
 * featured cards sit ABOVE the text, so after reading there was no shop link
 * (11/9 design review). Compact rows, 44px buttons, PR notice right before the
 * first shop link. placement "guide_end" keeps it separable in by_placement.
 * No superlatives; price changes are stated, not hidden.
 */
export default function GuideEndShops({ products, listSource }: { products: Product[]; listSource: string }) {
  const rows = products.filter((p) => p.affiliate_url && p.current_price !== null).slice(0, 3);
  if (rows.length === 0) return null;

  return (
    <section className="mt-12 rounded-2xl border border-border bg-card p-4 sm:p-6" aria-labelledby="guide-end-shops">
      <h2 id="guide-end-shops" className="font-display text-base font-semibold text-foreground">
        記事の商品を店で確かめる
      </h2>
      <PrNotice className="mt-3" />
      <ul className="mt-4 flex flex-col gap-3">
        {rows.map((p) => {
          const shop = shopOf(p.affiliate_url as string);
          return (
            <li key={p.id} className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div className="min-w-0">
                <p className="line-clamp-2 text-sm font-semibold text-foreground">{displayName(p)}</p>
                <p className="font-num text-sm text-foreground/80">
                  ¥{(p.current_price as number).toLocaleString("ja-JP")}
                  <span className="ml-2 text-xs text-foreground/70">掲載時点・価格は変わります</span>
                </p>
              </div>
              <TrackedCta
                href={p.affiliate_url as string}
                target="_blank"
                rel="noopener noreferrer sponsored"
                className="btn-shop tap inline-flex min-h-11 shrink-0 items-center justify-center whitespace-nowrap rounded-full px-5 py-2.5 text-[13px] font-semibold"
                event="cta_click"
                params={{
                  product_id: p.id,
                  product_slug: p.slug,
                  product_name: p.name,
                  cta_type: "affiliate",
                  shop: shop.key,
                  buy_score: p.buy_score,
                  list_source: listSource,
                }}
                productId={p.id}
                category={p.category}
                placement="guide_end"
              >
                {shop.label}で価格を見る
              </TrackedCta>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
