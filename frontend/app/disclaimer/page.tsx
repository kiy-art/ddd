import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "運営者情報・免責事項 | ゴルフ買い時ナビ",
  description: "当サイトの運営方針、アフィリエイト表記、価格情報および買い時判定に関する免責事項です。",
};

export default function DisclaimerPage() {
  return (
    <article className="flex flex-col gap-8 text-sm leading-relaxed text-zinc-700 dark:text-zinc-300">
      <h1 className="text-2xl font-bold text-zinc-900 dark:text-white">運営者情報・免責事項</h1>

      <section className="flex flex-col gap-2">
        <h2 className="text-lg font-semibold text-zinc-900 dark:text-white">サイトについて</h2>
        <p>
          「ゴルフ買い時ナビ」は、ゴルフ用品の価格推移データをもとに、現在の価格が過去の傾向と比べて
          割安かどうかを一定のルールに基づき機械的に判定し、紹介する情報サイトです。
        </p>
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="text-lg font-semibold text-zinc-900 dark:text-white">アフィリエイトプログラムについて</h2>
        <p>
          当サイトは、Amazonアソシエイト・楽天アフィリエイト等のアフィリエイトプログラムに参加する予定です。
          商品ページ内の「購入ページを見る」等のリンクには、アフィリエイトリンクが含まれる場合があります。
          リンクを経由して商品を購入された場合、当サイト運営者が各ECサイトより紹介料を受け取ることがあります。
          紹介料の有無は、掲載価格や表示される情報の中立性には一切影響しません。
        </p>
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="text-lg font-semibold text-zinc-900 dark:text-white">価格・在庫情報について</h2>
        <ul className="list-disc space-y-1 pl-5">
          <li>掲載している価格・在庫状況は変動する可能性があります。</li>
          <li>実際の購入時には、必ず販売元サイトで最新の価格・在庫をご確認ください。</li>
          <li>価格の誤表示や情報の遅延によって生じたいかなる損害についても、当サイトは責任を負いかねます。</li>
        </ul>
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="text-lg font-semibold text-zinc-900 dark:text-white">買い時判定について</h2>
        <p>
          買い時判定は、過去30日間の価格データをもとにした機械的なルール（平均価格との比較等）により算出しており、
          将来の値動きを保証するものではありません。判定結果や説明文（AIによる自動生成を含む）は参考情報であり、
          購入を推奨・保証するものではありません。購入の最終判断はご自身の責任でお願いいたします。
        </p>
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="text-lg font-semibold text-zinc-900 dark:text-white">お問い合わせ</h2>
        <p>サイトに関するお問い合わせは、運営者までご連絡ください。</p>
      </section>
    </article>
  );
}
