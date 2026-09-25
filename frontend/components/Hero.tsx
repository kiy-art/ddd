import Link from "next/link";

import CountUp from "@/components/CountUp";
import GolfMotif from "@/components/GolfMotif";
import ProductPhotoCollage from "@/components/ProductPhotoCollage";

export default function Hero({
  productCount,
  avgDiscount,
  collageImages,
}: {
  productCount: number;
  avgDiscount: number | null;
  collageImages: (string | null | undefined)[];
}) {
  return (
    <section className="relative overflow-hidden bg-card">
      <ProductPhotoCollage images={collageImages} />
      <GolfMotif
        variant="dimples"
        className="pointer-events-none absolute -bottom-16 -right-10 h-64 w-64 text-brand/[0.06] sm:h-80 sm:w-80"
      />

      <div className="relative mx-auto flex max-w-7xl flex-col gap-10 px-6 py-24 sm:py-32 lg:py-40">
        <div className="flex max-w-2xl flex-col gap-6">
          <span className="text-xs font-medium uppercase tracking-[0.3em] text-accent">
            AI Golf Deal Intelligence
          </span>
          <h1 className="font-display text-4xl font-semibold leading-[1.1] tracking-tight text-foreground sm:text-6xl">
            今日、買うべき
            <br />
            ゴルフ用品をAIが発見。
          </h1>
          <p className="max-w-md text-base leading-relaxed text-foreground/60 sm:text-lg">
            「最安値」を探すサイトではありません。過去の価格データを毎日分析し、
            「今が買い時か」をスコアでお伝えします。
          </p>
          <div className="flex flex-wrap gap-3 pt-2">
            <Link
              href="#best-buy"
              className="rounded-full bg-brand px-7 py-3.5 text-sm font-semibold text-white transition-transform hover:scale-[1.03]"
            >
              今日の買い時を見る
            </Link>
            <Link
              href="#how-it-works"
              className="rounded-full border border-border px-7 py-3.5 text-sm font-semibold text-foreground/80 transition-colors hover:bg-background"
            >
              仕組みを見る
            </Link>
          </div>
        </div>

        <dl className="flex flex-wrap gap-x-12 gap-y-6 border-t border-border pt-8">
          <div>
            <dt className="text-xs uppercase tracking-widest text-foreground/45">Tracked Items</dt>
            <dd className="font-display text-3xl font-semibold text-foreground">
              <CountUp value={productCount} />
            </dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-widest text-foreground/45">Avg. Price Move</dt>
            <dd className="font-display text-3xl font-semibold text-foreground">
              {avgDiscount === null ? (
                "—"
              ) : (
                <CountUp value={avgDiscount} decimals={1} prefix={avgDiscount > 0 ? "+" : ""} suffix="%" />
              )}
            </dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-widest text-foreground/45">Updated</dt>
            <dd className="font-display text-3xl font-semibold text-foreground">Daily</dd>
          </div>
        </dl>
      </div>
    </section>
  );
}
