import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { CATEGORY_LABELS } from "@/lib/api";
import { GUIDES, getGuide } from "@/lib/guides";

export const revalidate = 0;

type Params = { slug: string };

export function generateStaticParams() {
  return GUIDES.map((guide) => ({ slug: guide.slug }));
}

export async function generateMetadata({ params }: { params: Promise<Params> }): Promise<Metadata> {
  const { slug } = await params;
  const guide = getGuide(slug);
  if (!guide) return {};

  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";
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
  const guide = getGuide(slug);
  if (!guide) notFound();

  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";
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
      <p className="mt-3 text-sm text-foreground/50">
        {new Date(guide.publishedAt).toLocaleDateString("ja-JP", { year: "numeric", month: "long", day: "numeric" })}
      </p>

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
