import type { Metadata } from "next";
import Link from "next/link";

const FAQS = [
  {
    q: "「買い時」はどうやって判定していますか？",
    a: "各商品の実際の価格の記録をもとに、30日平均との差、記録上の最安値との差、直近7日間の値動きなどから、機械的なルールで「買い時スコア」（1〜99）を算出しています。高いほど買い時で、80以上は「今が買い時」、65〜79は「買い時」、40〜64は「様子見」、39以下は「待つのが無難」です。商品ページでは、そのスコアになった根拠の数字も表示しています。将来の値動きを予測するものではなく、あくまで過去の価格水準と比べて今が割安かどうかの参考情報です。",
  },
  {
    q: "最安値を保証していますか？",
    a: "いいえ、当サイトは最安値を探す・保証するサイトではありません。掲載している価格は日々変動する可能性があるため、購入前には必ず販売元サイトで最新の価格をご確認ください。",
  },
  {
    q: "価格データはどこから取得していますか？",
    a: "楽天市場とYahoo!ショッピングの商品検索APIを通じて取得した実際の販売価格を、1日1回自動で記録しています（価格の推移は楽天市場の価格）。Amazonの価格は取得していません。手入力やAIによる価格の推測は行っていません。",
  },
  {
    q: "商品ページのAIによる説明文は信頼できますか？",
    a: "AIによる説明文は、実際の価格データ（現在価格・平均価格・買い時判定など）をもとに生成しており、価格やスペックを創作することはありません。ただし内容は参考情報であり、購入を保証・推奨するものではありません。",
  },
  {
    q: "商品リンクから購入すると何が起きますか？",
    a: "当サイトは楽天アフィリエイトとAmazonアソシエイト・プログラムに参加しており、リンク経由で商品を購入された場合、当サイト運営者が紹介料を受け取ることがあります（Yahoo!ショッピングへのリンクは現在、紹介料の対象外です）。紹介料の有無は掲載価格や表示される情報の中立性には一切影響しません。また、広告主の意向は買い時の判定に含まれません。詳しくは「免責事項・アフィリエイトについて」のページをご覧ください。",
  },
  {
    q: "掲載されている商品はどうやって選んでいますか？",
    a: "運営者が実際に調査して登録した商品に加え、楽天市場のカテゴリ検索から自動で候補を見つけています。自動で見つかった商品のうち、ブランドやカテゴリの判定などの厳しい条件を満たした一部は自動で公開し、それ以外は運営者が確認してから公開します。",
  },
  {
    q: "取り扱っているカテゴリ・ブランドは？",
    a: "ドライバー・アイアン・ウェッジ・パター・ボール・グローブ・距離計・その他の8カテゴリで、PING・Titleist・Callaway・TaylorMadeなど主要ブランドの商品を扱っています。掲載ブランドは順次拡大中です。",
  },
];

export const metadata: Metadata = {
  title: "よくある質問",
  description: "PAR.の買い時スコアの仕組み、価格データの取得元、アフィリエイトについてなど、よくある質問にお答えします。",
};

export default function FaqPage() {
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: FAQS.map((item) => ({
      "@type": "Question",
      name: item.q,
      acceptedAnswer: { "@type": "Answer", text: item.a },
    })),
  };

  return (
    <div className="mx-auto max-w-3xl px-6 py-16 sm:py-24">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />

      <p className="text-xs font-medium uppercase tracking-[0.3em] text-accent">FAQ</p>
      <h1 className="mt-2 font-display text-3xl font-semibold text-foreground">よくある質問</h1>

      <div className="mt-10 flex flex-col gap-8">
        {FAQS.map((item) => (
          <div key={item.q}>
            <h2 className="font-display text-base font-semibold text-foreground">{item.q}</h2>
            <p className="mt-2 text-sm leading-relaxed text-foreground/65">{item.a}</p>
          </div>
        ))}
      </div>

      <p className="mt-14 text-sm text-foreground/50">
        その他ご不明な点は
        <Link href="/disclaimer" className="mx-1 text-brand hover:underline">
          免責事項・アフィリエイトについて
        </Link>
        をご確認のうえ、
        <Link href="/contact" className="mx-1 text-brand hover:underline">
          お問い合わせフォーム
        </Link>
        からご連絡ください。
      </p>
    </div>
  );
}
