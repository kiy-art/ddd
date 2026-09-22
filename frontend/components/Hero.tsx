import Link from "next/link";

import CountUp from "@/components/CountUp";

export default function Hero({
  productCount,
  avgDiscount,
}: {
  productCount: number;
  avgDiscount: number | null;
}) {
  return (
    <section className="relative overflow-hidden bg-foreground text-white">
      {/* Abstract arc motif echoing the AI Buy Signal gauge — no stock photography needed */}
      <svg
        className="pointer-events-none absolute -right-40 -top-40 h-[640px] w-[640px] opacity-[0.16] sm:-right-20"
        viewBox="0 0 400 400"
        fill="none"
      >
        <circle cx="200" cy="200" r="180" stroke="white" strokeWidth="1" />
        <circle cx="200" cy="200" r="140" stroke="white" strokeWidth="1" />
        <circle cx="200" cy="200" r="100" stroke="#C1521A" strokeWidth="2" />
        <path d="M200 20 A180 180 0 0 1 380 200" stroke="#C1521A" strokeWidth="2" strokeLinecap="round" />
      </svg>

      <div className="relative mx-auto flex max-w-7xl flex-col gap-10 px-6 py-24 sm:py-32 lg:py-40">
        <div className="flex max-w-2xl flex-col gap-6">
          <span className="text-xs font-medium uppercase tracking-[0.3em] text-accent">
            AI Golf Deal Intelligence
          </span>
          <h1 className="font-display text-4xl font-semibold leading-[1.1] tracking-tight sm:text-6xl">
            今日、買うべき
            <br />
            ゴルフ用品をAIが発見。
          </h1>
          <p className="max-w-md text-base leading-relaxed text-white/70 sm:text-lg">
            「最安値」を探すサイトではありません。過去の価格データを毎日分析し、
            「今が買い時か」をスコアでお伝えします。
          </p>
          <div className="flex flex-wrap gap-3 pt-2">
            <Link
              href="#best-buy"
              className="rounded-full bg-white px-7 py-3.5 text-sm font-semibold text-brand transition-transform hover:scale-[1.03]"
            >
              今日の買い時を見る
            </Link>
            <Link
              href="#how-it-works"
              className="rounded-full border border-white/25 px-7 py-3.5 text-sm font-semibold text-white/90 transition-colors hover:bg-white/10"
            >
              仕組みを見る
            </Link>
          </div>
        </div>

        <dl className="flex flex-wrap gap-x-12 gap-y-6 border-t border-white/15 pt-8">
          <div>
            <dt className="text-xs uppercase tracking-widest text-white/50">Tracked Items</dt>
            <dd className="font-display text-3xl font-semibold">
              <CountUp value={productCount} />
            </dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-widest text-white/50">Avg. Price Move</dt>
            <dd className="font-display text-3xl font-semibold">
              {avgDiscount === null ? (
                "—"
              ) : (
                <CountUp value={avgDiscount} decimals={1} prefix={avgDiscount > 0 ? "+" : ""} suffix="%" />
              )}
            </dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-widest text-white/50">Updated</dt>
            <dd className="font-display text-3xl font-semibold">Daily</dd>
          </div>
        </dl>
      </div>
    </section>
  );
}
