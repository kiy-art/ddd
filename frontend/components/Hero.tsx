import Link from "next/link";

import CountUp from "@/components/CountUp";
import CtaArrow from "@/components/CtaArrow";
import GolfMotif from "@/components/GolfMotif";
import ProductPhotoCollage from "@/components/ProductPhotoCollage";

// STEP60 "Clean Fairway" hero (was STEP50's dark terminal panel): a pale
// mint wash with a faint measurement grid (.terminal-panel in globals.css),
// dark ink headline, and the site's real numbers as a row of white stat
// cards - bright and trustworthy rather than a black "trading terminal".
export default function Hero({
  productCount,
  avgDiscount,
  collageImages,
}: {
  productCount: number | null;
  avgDiscount: number | null;
  collageImages: (string | null | undefined)[];
}) {
  return (
    <section className="terminal-panel relative overflow-hidden">
      {/* The photo collage sits behind the copy; on a phone there's no room
          beside the headline, so it would only cover the text. */}
      <div className="hidden sm:block">
        <ProductPhotoCollage images={collageImages} />
      </div>
      <GolfMotif
        variant="dimples"
        className="pointer-events-none absolute -bottom-16 -right-10 h-64 w-64 text-brand/[0.08] sm:h-80 sm:w-80"
      />

      <div className="relative mx-auto flex max-w-7xl flex-col gap-12 px-6 py-20 sm:py-28 lg:py-36">
        <div className="flex max-w-2xl flex-col gap-6">
          <span className="inline-flex w-fit items-center gap-2 rounded-full border border-brand/20 bg-white/80 px-3 py-1 font-num text-[11px] font-medium uppercase tracking-[0.25em] text-brand shadow-sm">
            <span className="live-dot" aria-hidden="true" />
            Golf Price Analytics
          </span>
          <h1 className="font-display text-4xl font-bold leading-[1.12] tracking-tight text-foreground sm:text-6xl">
            今日、買うべき
            <br />
            {/* phrase-level spans: a narrow screen breaks between phrases,
                never leaving "見。" alone on the last line */}
            <span className="bg-gradient-to-r from-[#047857] via-[#059669] to-[#10b981] bg-clip-text text-transparent">
              <span className="inline-block">ゴルフ用品を</span>
              <span className="inline-block">AIが発見。</span>
            </span>
          </h1>
          <p className="max-w-md text-base leading-relaxed text-foreground/65 sm:text-lg">
            「最安値」を探すサイトではありません。過去の価格データを毎日分析し、
            「今が買い時か」をスコアでお伝えします。
          </p>
          <div className="flex flex-wrap gap-3 pt-2">
            <Link href="#best-buy" className="btn-shop rounded-full px-7 py-3.5 text-sm font-semibold">
              今日の買い時を見る
              <CtaArrow />
            </Link>
            <Link
              href="#how-it-works"
              className="btn-ghost tap inline-flex items-center rounded-full px-7 py-3.5 text-sm font-semibold text-foreground/80 hover:text-foreground"
            >
              仕組みを見る
            </Link>
          </div>
        </div>

        {/* Ticker strip: the site's real, current numbers. */}
        <dl className="grid max-w-3xl grid-cols-3 divide-x divide-border overflow-hidden rounded-2xl border border-border bg-white/90 shadow-[0_10px_30px_-18px_rgba(4,120,87,0.35)] backdrop-blur-sm">
          <div className="px-4 py-4 sm:px-6">
            <dt className="text-[10px] font-medium uppercase tracking-[0.2em] text-foreground/45 sm:text-[11px]">掲載中の商品</dt>
            <dd className="mt-1 font-num text-2xl font-semibold text-foreground sm:text-3xl">
              {productCount === null ? "—" : <CountUp value={productCount} />}
            </dd>
          </div>
          <div className="px-4 py-4 sm:px-6">
            <dt className="text-[10px] font-medium uppercase tracking-[0.2em] text-foreground/45 sm:text-[11px]">平均の値動き</dt>
            <dd
              className={`mt-1 font-num text-2xl font-semibold sm:text-3xl ${
                avgDiscount !== null && avgDiscount < 0 ? "text-brand" : "text-foreground"
              }`}
            >
              {avgDiscount === null ? (
                "—"
              ) : (
                <CountUp value={avgDiscount} decimals={1} prefix={avgDiscount > 0 ? "+" : ""} suffix="%" />
              )}
            </dd>
          </div>
          <div className="px-4 py-4 sm:px-6">
            <dt className="text-[10px] font-medium uppercase tracking-[0.2em] text-foreground/45 sm:text-[11px]">更新</dt>
            <dd className="mt-1 flex items-center gap-2 font-num text-2xl font-semibold text-foreground sm:text-3xl">
              毎日
            </dd>
          </div>
        </dl>
      </div>
    </section>
  );
}
