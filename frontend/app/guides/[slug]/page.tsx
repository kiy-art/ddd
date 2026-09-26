import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import FadeIn from "@/components/FadeIn";
import ProductCard from "@/components/ProductCard";
import { CATEGORY_LABELS, Product, getCategoryProducts, getProducts } from "@/lib/api";
import { computeDeals } from "@/lib/deals";
import { GUIDES, Guide, getGuideBySlug } from "@/lib/guides";
import { SITE_URL } from "@/lib/siteUrl";

export const revalidate = 0;

const DEFAULT_FEATURED_LIMIT = 6;

async function loadFeaturedProducts(
  featured: Guide["featured"]
): Promise<{ product: Product; caption?: string }[]> {
  if (!featured) return [];
  const limit = featured.limit ?? DEFAULT_FEATURED_LIMIT;

  try {
    if (featured.kind === "top_buy_signal" && featured.category) {
      const products = await getCategoryProducts(featured.category);
      return [...products]
        .sort((a, b) => (b.buy_signal_score ?? -1) - (a.buy_signal_score ?? -1))
        .slice(0, limit)
        .map((product) => ({ product }));
    }

    if (featured.kind === "price_drops") {
      const products = featured.category
        ? await getCategoryProducts(featured.category)
        : await getProducts();
      return computeDeals(products)
        .slice(0, limit)
        .map(({ product, dropPercent }) => ({ product, caption: `前回価格より ${dropPercent}% 値下がり` }));
    }
  } catch {
    return [];
  }

  return [];
}

type Params = { slug: string };

export function generateStaticParams() {
  return GUIDES.map((guide) => ({ slug: guide.slug }));
}

export async function generateMetadata({ params }: { params: Promise<Params> }): Promise<Metadata> {
  const { slug } = await params;
  const guide = await getGuideBySlug(slug);
  if (!guide) return {};

  const siteUrl = SITE_URL;
  const url = `${siteUrl}/guides/${guide.slug}`;

  return {
    title: guide.title,
    description: guide.description,
    alternates: { canonical: url },
    openGraph: { type: "article", url, title: guide.title, description: guide.description },
    twitter: { card: "summary_large_image", title: guide.title, description: guide.description },
  };
}

export default async function GuidePage({ params }: { params: Promise<Params> }) {
  const { slug } = await params;
  const guide = await getGuideBySlug(slug);
  if (!guide) notFound();

  const featuredProducts = await loadFeaturedProducts(guide.featured);

  const siteUrl = SITE_URL;
  const url = `${siteUrl}/guides/${guide.slug}`;

  const articleJsonLd = {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: guide.title,
    description: guide.description,
    datePublished: guide.publishedAt,
    dateModified: guide.publishedAt,
    author: { "@type": "Organization", name: "PAR." },
    publisher: { "@type": "Organization", name: "PAR." },
    mainEntityOfPage: url,
  };

  const breadcrumbJsonLd = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "PAR.", item: siteUrl },
      { "@type": "ListItem", position: 2, name: "購入ガイド", item: `${siteUrl}/guides` },
      { "@type": "ListItem", position: 3, name: guide.title, item: url },
    ],
  };

  return (
    <article className="mx-auto max-w-3xl px-6 py-16 sm:py-24">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(articleJsonLd) }} />
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbJsonLd) }} />

      <Link href="/guides" className="text-xs font-medium uppercase tracking-widest text-foreground/40 hover:text-brand">
        ← 購入ガイド一覧
      </Link>

      <h1 className="mt-4 font-display text-3xl font-semibold leading-snug text-foreground">{guide.title}</h1>
      <div className="mt-3 flex flex-wrap items-center gap-2 text-sm text-foreground/50">
        <span>
          {new Date(guide.publishedAt).toLocaleDateString("ja-JP", { year: "numeric", month: "long", day: "numeric" })}
        </span>
        {guide.isAiGenerated && (
          <span className="rounded-full border border-border px-2 py-0.5 text-xs font-medium text-foreground/60">
            AIが実データをもとに自動生成した記事です
          </span>
        )}
      </div>

      {guide.featured && (
        <div className="mt-10">
          <h2 className="font-display text-xl font-semibold text-foreground">{guide.featured.heading}</h2>
          {featuredProducts.length === 0 ? (
            <p className="mt-4 rounded-2xl border border-dashed border-border bg-card px-4 py-10 text-center text-sm text-foreground/50">
              現在、条件に合う商品がありません。しばらく時間をおいて再度ご確認ください。
            </p>
          ) : (
            <div className="mt-4 grid grid-cols-1 gap-5 sm:grid-cols-2">
              {featuredProducts.map(({ product, caption }, i) => (
                <FadeIn key={product.id} delay={(i % 6) * 60} className="flex flex-col gap-2">
                  {caption && (
                    <span className="px-1 text-xs font-semibold text-brand dark:text-brand-light">{caption}</span>
                  )}
                  <ProductCard product={product} listSource={`guide:${guide.slug}`} />
                </FadeIn>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="mt-10 flex flex-col gap-10">
        {guide.sections.map((section) => (
          <section key={section.heading}>
            <h2 className="font-display text-xl font-semibold text-foreground">{section.heading}</h2>
            <div className="mt-3 flex flex-col gap-3">
              {section.paragraphs.map((p, i) => (
                <p key={i} className="text-sm leading-relaxed text-foreground/70">
                  {p}
                </p>
              ))}
            </div>
          </section>
        ))}
      </div>

      {guide.relatedCategories && guide.relatedCategories.length > 0 && (
        <div className="mt-14 rounded-2xl border border-border bg-card p-6 sm:p-8">
          <h2 className="font-display text-base font-semibold text-foreground">関連するカテゴリを見る</h2>
          <div className="mt-3 flex flex-wrap gap-2">
            {guide.relatedCategories.map((c) => (
              <Link
                key={c}
                href={`/category/${c}`}
                className="rounded-full border border-border px-4 py-2 text-sm text-foreground/70 transition-colors hover:border-foreground/30 hover:text-foreground"
              >
                {CATEGORY_LABELS[c] ?? c}の一覧を見る
              </Link>
            ))}
            <Link
              href="/deals"
              className="rounded-full border border-border px-4 py-2 text-sm text-foreground/70 transition-colors hover:border-foreground/30 hover:text-foreground"
            >
              値下がり中の商品を見る
            </Link>
          </div>
        </div>
      )}
    </article>
  );
}
