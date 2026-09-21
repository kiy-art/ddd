import type { Metadata } from "next";
import Link from "next/link";

import { GUIDES } from "@/lib/guides";

export const metadata: Metadata = {
  title: "購入ガイド",
  description: "ゴルフクラブの買い替えタイミングや型落ち・中古の選び方など、購入前に知っておきたい情報をまとめました。",
};

export default function GuidesIndexPage() {
  return (
    <div className="mx-auto max-w-4xl px-6 py-16 sm:py-24">
      <p className="text-xs font-medium uppercase tracking-[0.3em] text-accent">Buying Guides</p>
      <h1 className="mt-2 font-display text-3xl font-semibold text-foreground">購入ガイド</h1>
      <p className="mt-4 max-w-2xl text-sm leading-relaxed text-foreground/60">
        ゴルフクラブをいつ・どう買うのが得なのか。型落ちモデルの選び方、買い替えタイミング、セール時期の傾向など、
        購入前に押さえておきたいポイントをまとめています。
      </p>

      <div className="mt-10 flex flex-col gap-4">
        {GUIDES.map((guide) => (
          <Link
            key={guide.slug}
            href={`/guides/${guide.slug}`}
            className="rounded-2xl border border-border bg-card p-6 transition-colors hover:border-foreground/20 sm:p-8"
          >
            <h2 className="font-display text-lg font-semibold text-foreground">{guide.title}</h2>
            <p className="mt-2 text-sm leading-relaxed text-foreground/60">{guide.description}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
