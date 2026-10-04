import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "免責事項・アフィリエイトについて",
  description: "当サイトの運営方針、アフィリエイト表記、価格情報および買い時判定に関する免責事項です。",
};

export default function DisclaimerPage() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-16 sm:py-24">
      <article className="flex flex-col gap-10 text-sm leading-relaxed text-foreground/70">
        <h1 className="font-display text-3xl font-semibold text-foreground">免責事項・アフィリエイトについて</h1>

        <section className="flex flex-col gap-2">
          <h2 className="font-display text-lg font-medium text-foreground">サイトについて</h2>
          <p>
            「PAR.」は、ゴルフ用品の価格推移データをもとに、現在の価格が過去の傾向と比べて
            割安かどうかを一定のルールに基づき機械的に判定し、紹介する情報サイトです。
          </p>
        </section>

        <section className="flex flex-col gap-2">
          <h2 className="font-display text-lg font-medium text-foreground">アフィリエイトプログラムについて</h2>
          {/* STEP74: brought in line with the links the site actually carries
              (Amazon has been tagged since STEP54; Yahoo! links are plain until
              ValueCommerce's sid/pid are set). The Amazon sentence is the
              commonly used required wording - its original in the Associates
              Operating Agreement is still to be checked by the operator (C2). */}
          <p>
            当サイトは、以下のアフィリエイトプログラムに参加しています。商品ページや一覧ページの各ショップへのリンクには、
            アフィリエイトリンクが含まれます。リンクを経由して商品を購入された場合、当サイト運営者が各社より
            紹介料を受け取ることがあります。紹介料の有無は、掲載価格や表示される情報の中立性には一切影響しません。
          </p>
          <ul className="list-disc space-y-1 pl-5">
            <li>楽天アフィリエイト（楽天市場へのリンク）</li>
            <li>Amazonアソシエイト・プログラム：Amazonのアソシエイトとして、PAR.は適格販売により収入を得ています。</li>
          </ul>
          <p>
            Yahoo!ショッピングへのリンクは、現在は紹介料の対象外です（通常のリンクです）。
          </p>
        </section>

        <section className="flex flex-col gap-2">
          <h2 className="font-display text-lg font-medium text-foreground">商品画像について</h2>
          <p>
            商品ページの画像は、楽天市場の商品検索API（楽天ウェブサービス）、またはYahoo!ショッピングの
            商品検索APIを通じて取得した、各商品の出品者自身による商品写真です。権利者に無断で第三者サイトから写真を
            転載・複製することは行っておりません。画像が取得できない商品については、
            カテゴリを表す簡易的なアイコンを代わりに表示しています。
          </p>
        </section>

        <section className="flex flex-col gap-2">
          <h2 className="font-display text-lg font-medium text-foreground">価格・在庫情報について</h2>
          <ul className="list-disc space-y-1 pl-5">
            <li>価格は、楽天市場とYahoo!ショッピングの商品検索APIから1日1回取得しています。Amazonの価格は取得していません。</li>
            <li>掲載している価格・在庫状況は変動する可能性があります。</li>
            <li>実際の購入時には、必ず販売元サイトで最新の価格・在庫をご確認ください。</li>
            <li>価格の誤表示や情報の遅延によって生じたいかなる損害についても、当サイトは責任を負いかねます。</li>
          </ul>
        </section>

        <section className="flex flex-col gap-2">
          <h2 className="font-display text-lg font-medium text-foreground">買い時判定について</h2>
          <p>
            買い時判定は、過去30日間の価格データをもとにした機械的なルール（平均価格との比較等）により算出しており、
            将来の値動きを保証するものではありません。判定結果や説明文（AIによる自動生成を含む）は参考情報であり、
            購入を推奨・保証するものではありません。購入の最終判断はご自身の責任でお願いいたします。
          </p>
        </section>

        <section className="flex flex-col gap-2">
          <h2 className="font-display text-lg font-medium text-foreground">お問い合わせ</h2>
          <p>
            サイトに関するお問い合わせは、
            <Link href="/contact" className="text-brand hover:underline">
              お問い合わせフォーム
            </Link>
            からご連絡ください。
          </p>
        </section>
      </article>
    </div>
  );
}
