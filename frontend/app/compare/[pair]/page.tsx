import type { Metadata } from "next";
import Link from "next/link";
import { notFound, permanentRedirect } from "next/navigation";

import CompareTable from "@/components/CompareTable";
import PageHeader from "@/components/PageHeader";
import { BUY_SCORE_LABELS, CATEGORY_LABELS, ProductDetail, getCategoryProducts, getProduct } from "@/lib/api";
import { PERFORMANCE_TYPE_LABELS, SKILL_LEVEL_LABELS } from "@/lib/badges";
import { pairCandidates, pairHref, pairSlug, nearestRivals } from "@/lib/comparePairs";
import { productDisplayName } from "@/lib/productSeo";
import { SITE_URL } from "@/lib/siteUrl";
import PrNotice from "@/components/PrNotice";

// STEP69: "A vs B" pages for searches like "Qi35 G440 比較 / 違い".
// Same category only. Every line of "違いのポイント" is built from stored
// facts (price, maker positioning, release date, listing specs, buy score)
// - nothing is written by AI and nothing is guessed; a fact one side
// lacks is simply not compared.

export const revalidate = 0;

type Params = { pair: string };

const THIN_DATA_DAYS = 7;
// Specs worth calling out as a difference (others stay in the table).
const KEY_SPECS: { key: string; label: string }[] = [
  { key: "loft", label: "ロフト角" },
  { key: "head_volume", label: "ヘッド体積" },
  { key: "weight", label: "クラブ重量" },
  { key: "length", label: "クラブ長さ" },
  { key: "construction", label: "構造" },
  { key: "cover", label: "カバー" },
];

function yen(value: number): string {
  return `¥${value.toLocaleString("ja-JP")}`;
}

async function loadPair(pair: string): Promise<[ProductDetail, ProductDetail] | null> {
  for (const [a, b] of pairCandidates(pair)) {
    const [pa, pb] = await Promise.allSettled([getProduct(a), getProduct(b)]);
    if (pa.status === "fulfilled" && pb.status === "fulfilled") {
      if (pa.value.category !== pb.value.category) return null;
      return [pa.value, pb.value];
    }
  }
  return null;
}

function releaseLabel(iso: string | null): string | null {
  if (!iso) return null;
  const [y, m] = iso.split("-").map(Number);
  return y && m ? `${y}年${m}月` : null;
}

function reliableScore(p: ProductDetail): number | null {
  return p.buy_score !== "insufficient_data" && p.history_span_days >= THIN_DATA_DAYS ? p.buy_signal_score : null;
}

function differencePoints(a: ProductDetail, b: ProductDetail): string[] {
  const nameA = productDisplayName(a);
  const nameB = productDisplayName(b);
  const points: string[] = [];

  if (a.current_price !== null && b.current_price !== null) {
    const diff = Math.abs(a.current_price - b.current_price);
    const cheaper = a.current_price < b.current_price ? nameA : nameB;
    points.push(
      diff === 0
        ? `現在価格はどちらも${yen(a.current_price)}です。`
        : `現在価格は${nameA}が${yen(a.current_price)}、${nameB}が${yen(b.current_price)}で、${cheaper}の方が${yen(diff)}安くなっています。`
    );
  }
  if (a.msrp && b.msrp && a.current_price !== null && b.current_price !== null) {
    const off = (p: ProductDetail) => Math.round(((p.current_price as number) - (p.msrp as number)) / (p.msrp as number) * 100);
    points.push(`メーカー希望小売価格との比較では、${nameA}が${off(a)}%、${nameB}が${off(b)}%です。`);
  }
  const level = (p: ProductDetail) => (p.skill_level ? SKILL_LEVEL_LABELS[p.skill_level] : null);
  if (level(a) && level(b)) {
    points.push(
      level(a) === level(b)
        ? `メーカーの位置づけは、どちらも「${level(a)}」です。`
        : `対象レベルは、${nameA}が「${level(a)}」、${nameB}が「${level(b)}」です。`
    );
  }
  const type = (p: ProductDetail) => (p.performance_type ? PERFORMANCE_TYPE_LABELS[p.performance_type] : null);
  if (type(a) && type(b) && type(a) !== type(b)) {
    points.push(`タイプは、${nameA}が「${type(a)}」、${nameB}が「${type(b)}」です。`);
  }
  const relA = releaseLabel(a.release_date);
  const relB = releaseLabel(b.release_date);
  if (relA && relB && a.release_date && b.release_date) {
    points.push(
      a.release_date === b.release_date
        ? `発売時期はどちらも${relA}です。`
        : `発売は${nameA}が${relA}、${nameB}が${relB}で、${a.release_date > b.release_date ? nameA : nameB}の方が新しいモデルです。`
    );
  }
  for (const { key, label } of KEY_SPECS) {
    const va = a.specs?.[key];
    const vb = b.specs?.[key];
    if (va && vb && va !== vb) points.push(`${label}は、${nameA}が${va}、${nameB}が${vb}です（販売ページ記載）。`);
  }
  const sa = reliableScore(a);
  const sb = reliableScore(b);
  if (sa !== null && sb !== null) {
    points.push(
      `PAR.の買い時スコアは、${nameA}が${sa}（${BUY_SCORE_LABELS[a.buy_score] ?? ""}）、${nameB}が${sb}（${BUY_SCORE_LABELS[b.buy_score] ?? ""}）です。`
    );
  }
  return points;
}

export async function generateMetadata({ params }: { params: Promise<Params> }): Promise<Metadata> {
  const { pair } = await params;
  const loaded = await loadPair(pair);
  if (!loaded) return {};
  const [a, b] = loaded;
  const nameA = productDisplayName(a);
  const nameB = productDisplayName(b);
  const url = `${SITE_URL}${pairHref(a.slug, b.slug)}`;
  const title = `${nameA} と ${nameB} を比較｜違い・スペック・価格・買い時`;
  const prices =
    a.current_price !== null && b.current_price !== null ? `現在価格は${yen(a.current_price)}と${yen(b.current_price)}。` : "";
  const description = `${nameA}と${nameB}の違いを、対象レベル・タイプ・スペック・価格推移・買い時スコアで比較。${prices}楽天市場・Yahoo!ショッピングの価格を毎日更新しています。`;
  return {
    title,
    description,
    alternates: { canonical: url },
    openGraph: { type: "website", url, title: `${title} - PAR.`, description },
    twitter: { card: "summary_large_image", title: `${title} - PAR.`, description },
  };
}

export default async function ComparePairPage({ params }: { params: Promise<Params> }) {
  const { pair } = await params;
  const loaded = await loadPair(pair);
  if (!loaded) notFound();
  const [a, b] = loaded;
  const canonical = pairSlug(a.slug, b.slug);
  if (pair !== canonical) permanentRedirect(`/compare/${canonical}`);
  const [first, second] = a.slug < b.slug ? [a, b] : [b, a];

  const nameA = productDisplayName(first);
  const nameB = productDisplayName(second);
  const label = CATEGORY_LABELS[first.category] ?? first.category;
  const points = differencePoints(first, second);

  let others: { slug: string; name: string; brand: string; with: ProductDetail }[] = [];
  try {
    const pool = await getCategoryProducts(first.category, undefined, 50);
    const rest = pool.filter((p) => p.slug !== first.slug && p.slug !== second.slug);
    others = [
      ...nearestRivals(first, rest, 2).map((p) => ({ slug: p.slug, name: p.name, brand: p.brand, with: first })),
      ...nearestRivals(second, rest, 2).map((p) => ({ slug: p.slug, name: p.name, brand: p.brand, with: second })),
    ];
  } catch {
    others = [];
  }
  others = others.filter(
    (o, i) => others.findIndex((x) => pairSlug(x.with.slug, x.slug) === pairSlug(o.with.slug, o.slug)) === i
  );

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "ホーム", item: SITE_URL },
      { "@type": "ListItem", position: 2, name: label, item: `${SITE_URL}/category/${first.category}` },
      { "@type": "ListItem", position: 3, name: `${nameA} と ${nameB} の比較`, item: `${SITE_URL}/compare/${canonical}` },
    ],
  };

  return (
    <div>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      <PageHeader
        eyebrow={`Compare / ${label}`}
        title={`${nameA} と ${nameB} の比較`}
        description="スペック・メーカーの位置づけ・価格・買い時スコアを、PAR.が記録した実データで並べて比較します。"
        collageImages={[first.image_url, second.image_url]}
      />

      <section className="px-6 py-12 sm:py-16">
        <div className="mx-auto max-w-7xl">
          {points.length > 0 && (
            <div className="card-lux mb-10 rounded-3xl p-6 sm:p-8">
              <span className="text-xs font-medium uppercase tracking-[0.3em] text-accent">Key Differences</span>
              <h2 className="mt-2 font-display text-xl font-semibold text-foreground sm:text-2xl">違いのポイント</h2>
              <ul className="mt-4 flex flex-col gap-2.5">
                {points.map((point) => (
                  <li key={point} className="flex gap-2.5 text-sm leading-relaxed text-foreground/75">
                    <span aria-hidden="true" className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-brand" />
                    {point}
                  </li>
                ))}
              </ul>
              <p className="mt-4 text-[11px] text-foreground/40">
                価格はPAR.が毎日取得した楽天市場の価格です。購入前に販売ページで最新の価格・在庫をご確認ください。
              </p>
            </div>
          )}

          <PrNotice className="mt-6" />
          <CompareTable products={[first, second]} placement="compare_pair" />

          <div className="mt-10 grid gap-3 sm:grid-cols-2">
            {[first, second].map((p) => (
              <Link
                key={p.slug}
                href={`/products/${p.slug}`}
                className="card-lux flex items-center justify-between rounded-2xl px-5 py-4 text-sm font-semibold text-foreground hover:text-brand"
              >
                {productDisplayName(p)}の価格推移・買い時を詳しく見る
                <span aria-hidden="true">→</span>
              </Link>
            ))}
          </div>

          {others.length > 0 && (
            <div className="mt-10">
              <h2 className="font-display text-lg font-semibold text-foreground">ほかの組み合わせで比較</h2>
              <div className="mt-3 flex flex-wrap gap-2">
                {others.map((o) => (
                  <Link
                    key={`${o.with.slug}-${o.slug}`}
                    href={pairHref(o.with.slug, o.slug)}
                    className="rounded-full border border-border px-4 py-2 text-xs text-foreground/70 hover:border-brand/40 hover:text-brand"
                  >
                    {o.with.name} vs {o.brand} {o.name}
                  </Link>
                ))}
              </div>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
