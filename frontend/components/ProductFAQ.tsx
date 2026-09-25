import Link from "next/link";

import { Product } from "@/lib/api";

function yen(value: number): string {
  return `¥${value.toLocaleString("ja-JP")}`;
}

/**
 * Generic Q&A about how the site's data/forecast work (true for every
 * product, so safe to state unconditionally) plus a couple of entries that
 * only render when this specific product actually has the underlying fact
 * (release_date / msrp) - never a guessed answer.
 */
export default function ProductFAQ({ product }: { product: Product }) {
  const faqs: { q: string; a: string }[] = [];

  if (product.release_date) {
    faqs.push({
      q: `${product.name}の発売日はいつですか？`,
      a: `${new Date(product.release_date).toLocaleDateString("ja-JP")}に発売されました。`,
    });
  }
  if (product.msrp !== null) {
    faqs.push({
      q: "メーカー希望小売価格はいくらですか？",
      a: `${yen(product.msrp)}（税込）です。実際の販売価格はこれより安くなる場合があります。`,
    });
  }
  faqs.push({
    q: "価格情報はどのくらいの頻度で更新されますか？",
    a: "楽天市場の価格情報をもとに、1日1回自動で価格を取得・記録しています。表示価格と実際の販売価格にタイムラグが生じる場合があるため、購入前に販売ページでご確認ください。",
  });
  faqs.push({
    q: "「買い時」の判定はどのように行っていますか？",
    a: "この商品自身の過去の価格データ（30日平均・過去最安値・直近の値動き）をもとに、あらかじめ決めたルールで機械的に算出しています。編集部の主観や広告主の意向は判定に含まれません。",
  });
  faqs.push({
    q: "価格予測はどの程度信頼できますか？",
    a: "この商品自身の価格データの量・期間に応じて「高・中・低」の確信度を表示しています。将来価格を保証するものではなく、あくまで過去データからの推測です。詳しくは価格予測セクションをご覧ください。",
  });

  return (
    <div>
      <span className="text-xs font-medium uppercase tracking-[0.3em] text-accent">FAQ</span>
      <h2 className="mt-2 font-display text-2xl font-semibold text-foreground">よくある質問</h2>
      <dl className="mt-6 flex flex-col divide-y divide-border">
        {faqs.map((faq) => (
          <div key={faq.q} className="py-4 first:pt-0 last:pb-0">
            <dt className="font-display text-sm font-semibold text-foreground">Q. {faq.q}</dt>
            <dd className="mt-1.5 text-sm leading-relaxed text-foreground/60">A. {faq.a}</dd>
          </div>
        ))}
      </dl>
      <Link href="/faq" className="mt-4 inline-block text-sm font-semibold text-brand hover:underline">
        サイト全体のよくある質問はこちら →
      </Link>
    </div>
  );
}
