import Link from "next/link";

import CountUp from "@/components/CountUp";
import CtaArrow from "@/components/CtaArrow";
import GolfMotif from "@/components/GolfMotif";
import ProductPhotoCollage from "@/components/ProductPhotoCollage";

// STEP50 "Fairway Terminal" hero: an obsidian instrument panel (faint
// measurement grid + emerald horizon glow, .terminal-panel in globals.css)
// with the site's real numbers set as a monospace ticker strip. Text colors
// here are fixed light values, not --foreground: this panel stays dark in
// both page themes (same rule as --ink).
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
    <section className="terminal-panel relative overflow-hidden">
      {/* The photo collage sits behind the copy; on a phone there's no room
          beside the headline, so it would only cover the text. */}
      <div className="hidden sm:block">
        <ProductPhotoCollage images={collageImages} />
      </div>
      <GolfMotif
        variant="dimples"
        className="pointer-events-none absolute -bottom-16 -right-10 h-64 w-64 text-[#10b981]/[0.08] sm:h-80 sm:w-80"
      />

      <div className="relative mx-auto flex max-w-7xl flex-col gap-12 px-6 py-20 sm:py-28 lg:py-36">
        <div className="flex max-w-2xl flex-col gap-6">
          <span className="inline-flex w-fit items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 font-num text-[11px] font-medium uppercase tracking-[0.25em] text-[#6ee7b7]">
            <span className="live-dot" aria-hidden="true" />
            Golf Price Analytics
          </span>
          <h1 className="font-display text-4xl font-bold leading-[1.12] tracking-tight text-[#f2f6f4] sm:text-6xl">
            今日、買うべき
            <br />
            {/* phrase-level spans: a narrow screen breaks between phrases,
                never leaving "見。" alone on the last line */}
            <span className="bg-gradient-to-r from-[#6ee7b7] via-[#34d399] to-[#10b981] bg-clip-text text-transparent">
              <span className="inline-block">ゴルフ用品を</span>
              <span className="inline-block">AIが発見。</span>
            </span>
          </h1>
          <p className="max-w-md text-base leading-relaxed text-white/60 sm:text-lg">
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
              className="tap inline-flex items-center rounded-full border border-white/15 px-7 py-3.5 text-sm font-semibold text-white/80 hover:border-[#34d399]/60 hover:text-white"
            >
              仕組みを見る
            </Link>
          </div>
        </div>

        {/* Ticker strip: the site's real, current numbers. */}
        <dl className="grid max-w-3xl grid-cols-3 divide-x divide-white/10 overflow-hidden rounded-2xl border border-white/10 bg-white/[0.03] backdrop-blur-sm">
          <div className="px-4 py-4 sm:px-6">
            <dt className="text-[10px] font-medium uppercase tracking-[0.2em] text-white/40 sm:text-[11px]">追跡中の商品</dt>
            <dd className="mt-1 font-num text-2xl font-semibold text-[#f2f6f4] sm:text-3xl">
              <CountUp value={productCount} />
            </dd>
          </div>
          <div className="px-4 py-4 sm:px-6">
            <dt className="text-[10px] font-medium uppercase tracking-[0.2em] text-white/40 sm:text-[11px]">平均の値動き</dt>
            <dd
              className={`mt-1 font-num text-2xl font-semibold sm:text-3xl ${
                avgDiscount !== null && avgDiscount < 0 ? "text-[#34d399]" : "text-[#f2f6f4]"
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
            <dt className="text-[10px] font-medium uppercase tracking-[0.2em] text-white/40 sm:text-[11px]">更新</dt>
            <dd className="mt-1 flex items-center gap-2 font-num text-2xl font-semibold text-[#f2f6f4] sm:text-3xl">
              毎日
            </dd>
          </div>
        </dl>
      </div>
    </section>
  );
}
