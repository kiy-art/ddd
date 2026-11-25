import TrackedCta from "@/components/TrackedCta";
import type { ProductDetail } from "@/lib/api";
import { displayName } from "@/lib/displayName";
import { getShopOffers } from "@/lib/shopOffers";
import { formatUpdatedAt } from "@/lib/shopRows";

// P-014: the two products' current Rakuten price and buy button, placed ABOVE
// the comparison table (the table's own buttons sit at its very bottom, so on
// /compare/[pair] visitors rarely reached them). Clicks are recorded with
// placement "compare_pair_top" (the table's bottom buttons keep "compare_pair") through the same TrackedCta -> trackAffiliateClick
// path as every other placement. The URL is the product's existing
// affiliate_url - no new URL is built. A product with no fresh Rakuten price
// (getShopOffers drops stale/missing ones) gets no button, only a note.
// The page renders <PrNotice /> directly above this block.
export default function CompareTopOffers({ products }: { products: ProductDetail[] }) {
  return (
    <div className="mb-6 grid gap-3 sm:grid-cols-2">
      {products.map((p) => {
        const lastPriceUpdatedAt =
          p.price_history.length > 0 ? p.price_history[p.price_history.length - 1].recorded_at : null;
        const offer = getShopOffers(p, lastPriceUpdatedAt).find((o) => o.shop === "rakuten") ?? null;
        const at = offer ? formatUpdatedAt(offer.updatedAt) : null;
        return (
          <div key={p.id} className="card-lux flex flex-col gap-2 rounded-2xl p-5">
            <p className="line-clamp-2 text-sm font-semibold text-foreground">{displayName(p)}</p>
            {offer ? (
              <>
                <p className="font-num text-2xl font-semibold text-foreground">
                  {`¥${offer.price.toLocaleString("ja-JP")}`}
                </p>
                <p className="text-[11px] text-foreground/50">
                  楽天市場の価格{at ? `（${at}時点）` : ""}。送料・ポイントは含みません。購入前に販売ページで最新の価格・在庫をご確認ください。
                </p>
                <TrackedCta
                  href={offer.url}
                  target="_blank"
                  rel="noopener noreferrer sponsored"
                  className="mt-1 block w-full rounded-full bg-brand px-4 py-3 text-center text-xs font-semibold text-on-brand transition-transform hover:scale-[1.03]"
                  event="cta_click"
                  params={{ product_id: p.id, product_slug: p.slug, cta_type: "affiliate_compare" }}
                  productId={p.id}
                  category={p.category}
                  placement="compare_pair_top"
                >
                  楽天市場で見る
                </TrackedCta>
              </>
            ) : (
              <p className="text-xs text-foreground/50">最新の楽天市場の価格を確認中です。</p>
            )}
          </div>
        );
      })}
    </div>
  );
}
