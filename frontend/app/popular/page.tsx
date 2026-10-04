import type { Metadata } from "next";
import Link from "next/link";

import CtaArrow from "@/components/CtaArrow";
import FadeIn from "@/components/FadeIn";
import PageHeader from "@/components/PageHeader";
import ProductCard from "@/components/ProductCard";
import SafeProductImage from "@/components/SafeProductImage";
import TrackedCta from "@/components/TrackedCta";
import {
  BUY_SCORE_LABELS,
  CATEGORY_LABELS,
  Product,
  RakutenRankingCategory,
  RakutenRankingEntry,
  getProducts,
  getRakutenRanking,
} from "@/lib/api";
import { freshPopularityRank, parseUtc } from "@/lib/popularity";

export const revalidate = 0;

// Same threshold ProductCard/product page use for "enough data to claim a
// trend" - kept local rather than shared since each of these files already
// defines its own copy of this constant (see ProductCard.tsx).
const THIN_DATA_DAYS = 7;
// How many ranking positions to show before "もっと見る" (the backend keeps 30).
const INITIAL_ROWS = 10;

export const metadata: Metadata = {
  title: "人気ランキング｜楽天市場の売れ筋ゴルフ用品",
  description:
    "楽天市場のカテゴリ別売れ筋ランキング（ドライバー・アイアン・ウェッジ・パター・ボール）を毎日更新。価格とレビュー、PAR.の買い時判定もあわせて確認できます。",
  // STEP74: X posts link here with utm/category query strings - one canonical page.
  alternates: { canonical: "/popular" },
};

function yen(value: number | null): string {
  return value === null ? "-" : `¥${value.toLocaleString("ja-JP")}`;
}

function isPriceDropping(p: Product): boolean {
  if (p.msrp !== null && p.current_price !== null && p.current_price < p.msrp) return true;
  const reliable = p.buy_score !== "insufficient_data" && p.history_span_days >= THIN_DATA_DAYS;
  return reliable && p.price_change_percent !== null && p.price_change_percent < 0;
}

// A plain helper (not inline in the component) so the clock read inside
// freshPopularityRank doesn't trip the purity lint rule.
function popularAndDropping(products: Product[]): Product[] {
  const ranks = new Map(products.map((p) => [p.id, freshPopularityRank(p)]));
  return products
    .filter((p) => ranks.get(p.id) != null && isPriceDropping(p))
    .sort((a, b) => (ranks.get(a.id) ?? 999) - (ranks.get(b.id) ?? 999));
}

function fetchedLabel(iso: string): string {
  return new Date(parseUtc(iso)).toLocaleString("ja-JP", {
    timeZone: "Asia/Tokyo",
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function RankBadge({ rank }: { rank: number }) {
  const podium =
    rank === 1
      ? "bg-[#c9a227] text-[#1a1405]"
      : rank === 2
        ? "bg-[#a8b3b0] text-[#101614]"
        : rank === 3
          ? "bg-[#b0774a] text-white"
          : "bg-foreground/[0.07] text-foreground/60";
  return (
    <span
      className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl font-num text-sm font-bold ${podium}`}
      aria-label={`${rank}位`}
    >
      {rank}
    </span>
  );
}

function RankingRow({ entry, category }: { entry: RakutenRankingEntry; category: string }) {
  return (
    <li className="card-lux flex flex-col gap-3 rounded-2xl p-3 sm:flex-row sm:items-center sm:gap-5 sm:p-4">
      <div className="flex min-w-0 flex-1 items-center gap-3 sm:gap-4">
        <RankBadge rank={entry.rank} />
        <div className="relative h-16 w-16 shrink-0 overflow-hidden rounded-xl bg-white sm:h-20 sm:w-20">
          <SafeProductImage src={entry.image_url} alt={entry.name} category={category} className="object-contain p-1.5" compact />
        </div>
        <div className="min-w-0 flex-1">
          <p className="line-clamp-2 text-sm font-semibold leading-snug text-foreground">{entry.name}</p>
          <p className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[11px] text-foreground/45">
            {entry.shop_name && <span>{entry.shop_name}</span>}
            {entry.review_average !== null && entry.review_count !== null && entry.review_count > 0 && (
              <span>
                <span className="text-[#c9a227]">★</span>
                <span className="font-num">{entry.review_average.toFixed(1)}</span>（{entry.review_count}件）
              </span>
            )}
            {entry.product_slug && entry.product_buy_score && (
              <span className="rounded-full bg-brand/10 px-2 py-0.5 font-semibold text-brand dark:text-brand-light">
                PAR.判定：{BUY_SCORE_LABELS[entry.product_buy_score] ?? "データ収集中"}
              </span>
            )}
          </p>
        </div>
      </div>
      <div className="flex items-center gap-3 sm:justify-end">
        <span className="shrink-0 font-num text-lg font-semibold text-foreground sm:w-28 sm:text-right">
          {yen(entry.price)}
        </span>
        <div className="flex flex-1 flex-col gap-1.5 sm:w-44 sm:flex-none">
          <TrackedCta
            href={entry.url}
            target="_blank"
            rel="noopener noreferrer sponsored"
            className="btn-shop tap whitespace-nowrap rounded-full px-4 py-2.5 text-center text-sm font-semibold"
            event="cta_click"
            params={{ cta_type: "affiliate", shop: "rakuten", ranking_category: category, rank: entry.rank, product_name: entry.name }}
            category={category}
            placement="popular_rakuten_ranking"
          >
            楽天で見る
            <CtaArrow className="h-3.5 w-3.5" />
          </TrackedCta>
          {entry.product_slug && (
            <Link
              href={`/products/${entry.product_slug}`}
              className="text-center text-[11px] font-semibold text-foreground/50 hover:text-brand dark:hover:text-brand-light"
            >
              価格推移・他店比較を見る →
            </Link>
          )}
        </div>
      </div>
    </li>
  );
}

export default async function PopularPage({
  searchParams,
}: {
  searchParams: Promise<{ category?: string; all?: string }>;
}) {
  const params = await searchParams;

  let ranking: RakutenRankingCategory[] = [];
  let products: Product[] = [];
  let error: string | null = null;
  try {
    [ranking, products] = await Promise.all([getRakutenRanking(30), getProducts({ limit: 200 })]);
  } catch {
    error = "ランキングの取得に失敗しました。しばらくしてから再度お試しください。";
  }

  const active = ranking.find((g) => g.category === params.category) ?? ranking[0] ?? null;
  const showAll = params.all === "1";
  const rows = active ? (showAll ? active.entries : active.entries.slice(0, INITIAL_ROWS)) : [];
  const dropping = popularAndDropping(products);

  return (
    <div>
      <PageHeader
        eyebrow="Popular"
        title="人気ランキング"
        description={`楽天市場のカテゴリ別売れ筋ランキングを毎日取得して掲載しています。当サイト独自の順位ではありません。${
          active ? `（ランキング取得：${fetchedLabel(active.fetched_at)}）` : ""
        }`}
        collageImages={active ? active.entries.slice(0, 6).map((e) => e.image_url) : []}
      />

      {error && (
        <div className="mx-auto max-w-7xl px-6 py-16">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}

      {!error && !active && (
        <div className="mx-auto max-w-7xl px-6 py-16">
          <p className="rounded-2xl border border-dashed border-border bg-card px-4 py-16 text-center text-sm text-foreground/50">
            楽天市場の売れ筋ランキングを準備中です。ランキングは毎朝更新されます。
          </p>
        </div>
      )}

      {active && (
        <section className="px-6 py-12 sm:py-16">
          <div className="mx-auto max-w-5xl">
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div>
                <span className="text-xs font-medium uppercase tracking-[0.3em] text-accent">Rakuten Bestsellers</span>
                <h2 className="mt-2 font-display text-2xl font-semibold text-foreground sm:text-3xl">
                  {CATEGORY_LABELS[active.category] ?? active.category}の売れ筋ランキング
                </h2>
              </div>
              <span className="rounded border border-foreground/30 px-1.5 py-0.5 text-[11px] font-semibold text-foreground/70">PR</span>
            </div>

            {/* Category tabs - scroll sideways on a phone. */}
            <nav aria-label="カテゴリ" className="-mx-6 mt-6 overflow-x-auto px-6 sm:mx-0 sm:px-0">
              <div className="inline-flex gap-1 rounded-full border border-border bg-card p-1">
                {ranking.map((g) => (
                  <Link
                    key={g.category}
                    href={`/popular?category=${g.category}`}
                    aria-current={g.category === active.category ? "page" : undefined}
                    className={`tap whitespace-nowrap rounded-full px-4 py-2 text-sm font-semibold ${
                      g.category === active.category ? "bg-brand text-on-brand" : "text-foreground/55 hover:text-foreground"
                    }`}
                  >
                    {CATEGORY_LABELS[g.category] ?? g.category}
                  </Link>
                ))}
              </div>
            </nav>

            <ol className="mt-6 flex flex-col gap-2">
              {rows.map((entry) => (
                <RankingRow key={entry.rank} entry={entry} category={active.category} />
              ))}
            </ol>

            {!showAll && active.entries.length > INITIAL_ROWS && (
              <div className="mt-6 text-center">
                <Link
                  href={`/popular?category=${active.category}&all=1`}
                  className="btn-ghost tap inline-flex rounded-full px-6 py-3 text-sm font-semibold text-foreground/80 hover:text-foreground"
                >
                  {active.entries.length}位までもっと見る
                </Link>
              </div>
            )}

            <p className="mt-6 text-xs leading-relaxed text-foreground/65">
              順位・価格・レビューは楽天市場の売れ筋ランキングAPIから取得した時点の情報です（毎日更新）。価格・在庫は変動するため、購入前に販売ページでご確認ください。
              ※広告・PRを含みます。リンク経由の購入により当サイトが紹介料を受け取ることがあります。
            </p>
            <p className="mt-2 text-[11px] text-foreground/40">
              <a href="https://developers.rakuten.com/" target="_blank" rel="noopener noreferrer" className="underline">
                Supported by Rakuten Developers
              </a>
            </p>
          </div>
        </section>
      )}

      {!error && dropping.length > 0 && (
        <section className="border-t border-border px-6 py-16 sm:py-20">
          <div className="mx-auto max-w-7xl">
            <FadeIn className="flex flex-col gap-3">
              <span className="text-xs font-medium uppercase tracking-[0.3em] text-sale">Popular &amp; Dropping</span>
              <h2 className="max-w-lg font-display text-3xl font-semibold leading-tight text-foreground sm:text-4xl">
                人気なのに値下がり中
              </h2>
              <p className="max-w-lg text-sm text-foreground/55">
                楽天市場の売れ筋ランキングに入っていて、PAR.の価格記録で値下がりしている商品です。
              </p>
            </FadeIn>
            <div className="mt-10 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {dropping.map((product, i) => (
                <FadeIn key={product.id} delay={i * 90}>
                  <ProductCard product={product} listSource="popular_dropping" />
                </FadeIn>
              ))}
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
