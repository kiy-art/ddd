import type { Metadata } from "next";
import Link from "next/link";

import { listAllGuides } from "@/lib/guides";

export const revalidate = 0;

export const metadata: Metadata = {
  title: "購入ガイド",
  description: "ゴルフクラブの買い替えタイミングや型落ち・中古の選び方など、購入前に知っておきたい情報をまとめました。",
};

export default async function GuidesIndexPage() {
  const guides = await listAllGuides();
  const featuredGuides = guides.filter((guide) => guide.featured);
  const evergreenGuides = guides.filter((guide) => !guide.featured);

  return (
    <div className="mx-auto max-w-4xl px-6 py-16 sm:py-24">
      <p className="text-xs font-medium uppercase tracking-[0.3em] text-accent">Buying Guides</p>
      <h1 className="mt-2 font-display text-3xl font-semibold text-foreground">購入ガイド</h1>
      <p className="mt-4 max-w-2xl text-sm leading-relaxed text-foreground/60">
        ゴルフクラブをいつ・どう買うのが得なのか。型落ちモデルの選び方、買い替えタイミング、セール時期の傾向など、
        購入前に押さえておきたいポイントをまとめています。
      </p>

      {featuredGuides.length > 0 && (
        <div className="mt-12">
          <h2 className="font-display text-lg font-semibold text-foreground">特集</h2>
          <p className="mt-1 text-sm text-foreground/50">実際の価格データに基づいた、今チェックしたい商品の特集です。</p>
          <div className="mt-5 flex flex-col gap-4">
            {featuredGuides.map((guide) => (
              <Link
                key={guide.slug}
                href={`/guides/${guide.slug}`}
                className="rounded-2xl border border-brand/30 bg-card p-6 transition-colors hover:border-brand/60 sm:p-8"
              >
                <h3 className="font-display text-lg font-semibold text-foreground">
                  {guide.title}
                  {guide.isAiGenerated && (
                    <span className="ml-2 rounded-full border border-border px-2 py-0.5 align-middle text-xs font-medium text-foreground/50">
                      AI自動生成
                    </span>
                  )}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-foreground/60">{guide.description}</p>
              </Link>
            ))}
          </div>
        </div>
      )}

      <div className="mt-12">
        {featuredGuides.length > 0 && <h2 className="font-display text-lg font-semibold text-foreground">購入ガイド</h2>}
        <div className="mt-5 flex flex-col gap-4">
          {evergreenGuides.map((guide) => (
            <Link
              key={guide.slug}
              href={`/guides/${guide.slug}`}
              className="rounded-2xl border border-border bg-card p-6 transition-colors hover:border-foreground/20 sm:p-8"
            >
              <h3 className="font-display text-lg font-semibold text-foreground">
                {guide.title}
                {guide.isAiGenerated && (
                  <span className="ml-2 rounded-full border border-border px-2 py-0.5 align-middle text-xs font-medium text-foreground/50">
                    AI自動生成
                  </span>
                )}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-foreground/60">{guide.description}</p>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
