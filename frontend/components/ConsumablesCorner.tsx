import Link from "next/link";

import CtaArrow from "@/components/CtaArrow";
import SafeProductImage from "@/components/SafeProductImage";
import TrackedCta from "@/components/TrackedCta";
import { ConsumablePick, ConsumablePicks, getConsumablePicks } from "@/lib/api";
import { getAmazonSearchUrl } from "@/lib/amazon";

// STEP52 "AIアナリティクス厳選" consumables corner - homepage bottom and
// below the product page's store comparison table.
//
// The picks, their discount and their copy all come from the backend
// (app/consumables_merchandiser.py), which only states a "% OFF" against a
// real basis: a verified maker list price, or PAR.'s own recorded 30-day
// median - and the struck-through price always says which. This component
// never computes or embellishes a discount of its own.
//
// Kept light on purpose: one small request with a short timeout, no chart,
// and on any failure (or fewer than 3 real picks) the corner simply isn't
// rendered - it's an extra, never something that can break the page.

const PICKS_TIMEOUT_MS = 4000;
const TITLE = "🤖 AIアナリティクス厳選：今週の買い足し・定番消耗品";

function yen(value: number): string {
  return `¥${value.toLocaleString("ja-JP")}`;
}

function priceDate(iso: string | null): string | null {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleDateString("ja-JP", { timeZone: "Asia/Tokyo", month: "numeric", day: "numeric" });
}

async function loadPicks(excludeProductId?: number): Promise<ConsumablePicks | null> {
  try {
    const data = await getConsumablePicks(
      { excludeProductId },
      { signal: AbortSignal.timeout(PICKS_TIMEOUT_MS) }
    );
    return data.picks.length >= 3 ? data : null;
  } catch {
    return null;
  }
}

function PickCard({ pick, placement }: { pick: ConsumablePick; placement: string }) {
  const trackingCategory = pick.kind === "ball" ? "ball" : undefined;
  const trackingParams = {
    product_name: `${pick.brand} ${pick.name}`,
    consumable_key: pick.key,
    consumable_kind: pick.kind,
  };
  const updated = priceDate(pick.price_updated_at);

  return (
    <article className="card-lux flex h-full w-[78vw] max-w-[320px] shrink-0 snap-start flex-col overflow-hidden rounded-3xl sm:w-auto sm:max-w-none">
      <div className="relative aspect-[4/3] w-full overflow-hidden bg-white">
        <SafeProductImage
          src={pick.image_url}
          alt={`${pick.brand} ${pick.name}`}
          category={pick.kind}
          className="object-contain p-6"
        />
        {pick.discount_badge && (
          <span className="absolute left-3 top-3 rounded-full bg-sale px-3 py-1.5 font-num text-sm font-bold tracking-tight text-white shadow-[0_8px_20px_-10px_rgba(194,65,45,0.9)]">
            {pick.discount_badge}
          </span>
        )}
      </div>

      <div className="flex flex-1 flex-col gap-3 p-5">
        <span className="inline-flex w-fit items-center gap-1.5 rounded-full border border-brand/25 bg-brand/[0.06] px-2.5 py-1 text-[11px] font-semibold text-brand dark:text-brand-light">
          <span aria-hidden="true">✦</span>
          AI注目：{pick.ai_tag}
        </span>

        <div>
          <span className="text-[11px] font-medium uppercase tracking-widest text-foreground/40">
            {pick.kind_label} · {pick.brand}
          </span>
          <h3 className="mt-0.5 line-clamp-2 font-display text-base font-semibold leading-snug text-foreground">
            {pick.name}
          </h3>
        </div>

        <div className="flex flex-col gap-1">
          {pick.reference_price !== null && pick.discount_badge && (
            <div className="flex flex-wrap items-baseline gap-x-2 text-xs text-foreground/45">
              <span className="font-num line-through">{yen(pick.reference_price)}</span>
              {pick.reference_label && <span>（{pick.reference_label}）</span>}
            </div>
          )}
          <div className="flex flex-wrap items-baseline gap-x-2">
            <span
              className={`font-num text-3xl font-semibold tracking-tight ${
                pick.discount_badge ? "text-sale" : "text-foreground"
              }`}
            >
              {yen(pick.current_price)}
            </span>
            <span className="text-[11px] text-foreground/40">
              楽天の価格{updated ? `・${updated}時点` : ""}
            </span>
          </div>
          {pick.savings_text && pick.discount_badge && (
            <span className="text-sm font-semibold text-sale">{pick.savings_text}！</span>
          )}
        </div>

        <p className="text-xs leading-relaxed text-foreground/55">{pick.micro_copy}</p>

        <div className="mt-auto flex flex-col gap-2 pt-2">
          {pick.rakuten_url && (
            <TrackedCta
              href={pick.rakuten_url}
              target="_blank"
              rel="noopener noreferrer sponsored"
              className="btn-shop rounded-full px-4 py-2.5 text-sm font-semibold"
              event="cta_click"
              params={{ ...trackingParams, cta_type: "affiliate" }}
              productId={pick.product_id ?? undefined}
              category={trackingCategory}
              placement={placement}
            >
              楽天で見る
              <CtaArrow className="h-3.5 w-3.5" />
            </TrackedCta>
          )}
          <TrackedCta
            href={getAmazonSearchUrl(pick.amazon_query)}
            target="_blank"
            rel="noopener noreferrer sponsored"
            className="btn-ghost rounded-full px-4 py-2.5 text-sm font-semibold text-foreground/75 hover:text-foreground"
            event="cta_click"
            params={{ ...trackingParams, cta_type: "affiliate_search" }}
            productId={pick.product_id ?? undefined}
            category={trackingCategory}
            placement={placement}
          >
            Amazonで探す
            <CtaArrow className="h-3.5 w-3.5" />
          </TrackedCta>
          {pick.product_slug && (
            <Link
              href={`/products/${pick.product_slug}`}
              className="pt-1 text-center text-xs font-semibold text-foreground/50 hover:text-brand dark:hover:text-brand-light"
            >
              価格推移と買い時スコアを見る →
            </Link>
          )}
        </div>
      </div>
    </article>
  );
}

export default async function ConsumablesCorner({
  variant,
  excludeProductId,
}: {
  // "home": a full-width page section; "product": sits inside the product
  // page's content column, under the store comparison table.
  variant: "home" | "product";
  excludeProductId?: number;
}) {
  const data = await loadPicks(excludeProductId);
  if (!data) return null;

  const placement = variant === "home" ? "consumables_home" : "consumables_product";
  const headingId = `consumables-corner-${variant}`;
  const columns = variant === "home" ? "sm:grid-cols-2 lg:grid-cols-3" : "sm:grid-cols-2 xl:grid-cols-3";

  const body = (
    <>
      <div className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="inline-flex items-center gap-2 rounded-full border border-border-strong bg-card px-3 py-1 font-num text-[11px] font-medium uppercase tracking-[0.25em] text-accent">
            <span className="live-dot" aria-hidden="true" />
            AI Picks
          </span>
          <span className="rounded-full bg-foreground/[0.06] px-2.5 py-1 text-[11px] font-semibold text-foreground/60">
            {data.season_label}
          </span>
          {data.sale_events.map((name) => (
            <span key={name} className="rounded-full bg-sale/10 px-2.5 py-1 text-[11px] font-semibold text-sale">
              {name}開催中
            </span>
          ))}
          <span className="rounded border border-border px-1.5 py-0.5 text-[10px] font-semibold text-foreground/45">PR</span>
        </div>
        <h2
          id={headingId}
          className={`font-display font-semibold leading-tight text-foreground ${
            variant === "home" ? "text-2xl sm:text-4xl" : "text-xl sm:text-2xl"
          }`}
        >
          {TITLE}
        </h2>
        <p className="max-w-2xl text-sm leading-relaxed text-foreground/55">
          PAR.が毎日記録している価格から、季節に合う消耗品をルールに基づいて選んでいます。
          「% OFF」は確認済みのメーカー希望小売価格、またはPAR.が記録した直近30日の中央値との比較です。
        </p>
      </div>

      {/* Phone: a swipeable row (snap), so six cards don't push the page
          footer far away; from sm up: a regular grid. */}
      <div
        className={`-mx-6 mt-8 flex snap-x snap-mandatory gap-4 overflow-x-auto px-6 pb-2 sm:mx-0 sm:grid sm:overflow-visible sm:px-0 sm:pb-0 ${columns}`}
      >
        {data.picks.map((pick) => (
          <PickCard key={pick.key} pick={pick} placement={placement} />
        ))}
      </div>

      <p className="mt-5 text-[11px] leading-relaxed text-foreground/40">
        ※価格・在庫は変動します。購入前に各販売ページでご確認ください。本コーナーのリンクにはアフィリエイトリンクが含まれます。
      </p>
    </>
  );

  if (variant === "product") {
    return (
      <section aria-labelledby={headingId} className="mt-10 border-t border-border pt-10">
        {body}
      </section>
    );
  }

  return (
    <section aria-labelledby={headingId} className="border-t border-border bg-background px-6 py-24 sm:py-32">
      <div className="mx-auto max-w-7xl">{body}</div>
    </section>
  );
}
