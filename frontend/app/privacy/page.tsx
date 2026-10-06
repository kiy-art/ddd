import type { Metadata } from "next";
import Link from "next/link";

// STEP75 (approval #003): the privacy policy. The facts here must match
// what the site actually does - when a data flow changes (a new form, a
// new external service, a different retention period), update this page
// in the same change and re-run the audit (docs/approvals/003).
// Retention periods: backend/app/retention.py. Hosting region: Render,
// Oregon (US). Consent checkbox: components/PriceAlertForm.tsx.

export const metadata: Metadata = {
  title: "プライバシーポリシー",
  description: "PAR.が取得する情報、利用目的、外部への送信、保存期間、停止・削除の方法について説明します。",
  alternates: { canonical: "/privacy" },
};

const SECTIONS = [
  { id: "basic", title: "基本方針" },
  { id: "operator", title: "運営者" },
  { id: "collect", title: "取得する情報" },
  { id: "purpose", title: "利用目的" },
  { id: "third-party", title: "第三者への提供" },
  { id: "overseas", title: "外部のサービスと、外国での取り扱い" },
  { id: "analytics", title: "アクセス解析（Googleアナリティクス）" },
  { id: "images", title: "商品画像の表示" },
  { id: "affiliate", title: "アフィリエイトリンクとCookie" },
  { id: "browser", title: "ブラウザ内に保存する情報" },
  { id: "retention", title: "保存期間と削除" },
  { id: "security", title: "安全管理" },
  { id: "requests", title: "開示・訂正・停止・削除のご請求" },
  { id: "changes", title: "改定とお問い合わせ窓口" },
];

const PPC_US_REPORT = "https://www.ppc.go.jp/enforcement/infoprovision/laws/offshore_report_america/";

function Section({ index, children }: { index: number; children: React.ReactNode }) {
  const section = SECTIONS[index];
  return (
    <section id={section.id} className="flex scroll-mt-24 flex-col gap-2">
      <h2 className="font-display text-lg font-medium text-foreground">
        {index + 1}. {section.title}
      </h2>
      {children}
    </section>
  );
}

const linkClass = "text-brand underline";

export default function PrivacyPage() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-16 sm:py-24">
      <article className="flex flex-col gap-10 text-sm leading-relaxed text-foreground/75">
        <div className="flex flex-col gap-3">
          <h1 className="font-display text-3xl font-semibold text-foreground">プライバシーポリシー</h1>
          <p>
            ゴルフ用品の価格比較サイト「PAR.」（https://par-gear.com、以下「当サイト」）が、利用者の情報をどのように扱うかを説明します。
          </p>
        </div>

        <nav aria-label="目次" className="rounded-2xl border border-border bg-card p-5">
          <p className="text-xs font-semibold text-foreground">目次</p>
          <ol className="mt-2 grid gap-1 text-sm sm:grid-cols-2">
            {SECTIONS.map((s, i) => (
              <li key={s.id}>
                <a href={`#${s.id}`} className="hover:text-brand hover:underline">
                  {i + 1}. {s.title}
                </a>
              </li>
            ))}
          </ol>
        </nav>

        <Section index={0}>
          <p>
            当サイトは、個人情報の保護に関する法律（個人情報保護法）その他の法令を守り、取得した情報を、下に書いた目的の範囲でだけ使います。
            必要のない情報は取得しません。
          </p>
        </Section>

        <Section index={1}>
          <ul className="list-disc space-y-1 pl-5">
            <li>運営者：PAR.（個人で運営しています）</li>
            <li>
              連絡先：
              <Link href="/contact" className={linkClass}>
                お問い合わせフォーム
              </Link>
            </li>
            <li>運営者の氏名・住所は、ご請求があれば、遅滞なくお知らせします。お問い合わせフォームからご連絡ください。</li>
          </ul>
        </Section>

        <Section index={2}>
          <p>当サイトが取得する情報は、次のとおりです。会員登録の機能はありません。</p>
          <ul className="list-disc space-y-2 pl-5">
            <li>
              <strong className="text-foreground">値下がり通知の登録</strong>
              ：メールアドレス、対象の商品、目標価格、登録の日時、プライバシーポリシーに同意した日時、通知を送った日時。
            </li>
            <li>
              <strong className="text-foreground">お問い合わせ</strong>
              ：お名前（任意）、メールアドレス、お問い合わせの内容、送信の日時。
            </li>
            <li>
              <strong className="text-foreground">ショップへのリンクのクリック</strong>
              ：どの商品の、どのショップへのリンクが、ページのどこで、いつ押されたか。このクリックの記録には、誰が押したかがわかる情報（メールアドレス・IPアドレスなど）を含めません（通信の記録は下のとおり）。
            </li>
            <li>
              <strong className="text-foreground">アクセス解析</strong>
              ：Googleアナリティクスによる閲覧の情報（
              <a href="#analytics" className={linkClass}>
                7.
              </a>
              ）。
            </li>
            <li>
              <strong className="text-foreground">通信の記録</strong>
              ：サイトを動かすサーバーの仕組みとして、ホスティング事業者（Render、米国）のシステムに、IPアドレス・ブラウザの種類・閲覧したURL・日時などの通信の記録が一定期間残ります。
            </li>
          </ul>
        </Section>

        <Section index={3}>
          <ul className="list-disc space-y-1 pl-5">
            <li>値下がり通知：目標価格以下になったことをメールでお知らせするため。通知の停止・削除のご依頼を受け付けるため。</li>
            <li>お問い合わせ：お問い合わせに対応する（返信を含む）ため。</li>
            <li>クリック・アクセス解析・通信の記録：サイトの利用状況を把握し、内容と使いやすさを改善するため。不正なアクセスを防ぐため。</li>
          </ul>
          <p>メールアドレスを、広告・宣伝のメールの送信や、上に書いていない目的に使うことはありません。</p>
        </Section>

        <Section index={4}>
          <p>
            取得した個人情報を、ご本人の同意なく第三者に提供することはありません。ただし、法令に基づく場合（裁判所・警察などから法令に基づく求めがあった場合など）と、利用目的の達成に必要な範囲で、業務を外部の事業者に任せる場合（
            <a href="#overseas" className={linkClass}>
              6.
            </a>
            ）は除きます。
          </p>
        </Section>

        <Section index={5}>
          <p>当サイトは、次の外部のサービスを使っています。いずれも事業者は米国にあります。</p>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[520px] border-collapse text-left text-xs">
              <thead>
                <tr className="border-b border-border text-foreground">
                  <th className="py-2 pr-3 font-semibold">サービス</th>
                  <th className="py-2 pr-3 font-semibold">使う目的</th>
                  <th className="py-2 font-semibold">扱う情報</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-border/60">
                  <td className="py-2 pr-3">Render（米国）</td>
                  <td className="py-2 pr-3">サイトとデータベースの運用（サーバーは米国オレゴン州）</td>
                  <td className="py-2">当サイトが保存するすべての情報（値下がり通知・お問い合わせを含む）、通信の記録</td>
                </tr>
                <tr className="border-b border-border/60">
                  <td className="py-2 pr-3">Resend（米国）</td>
                  <td className="py-2 pr-3">値下がり通知のメールの送信</td>
                  <td className="py-2">送信先のメールアドレス、メールの本文（商品名・価格）</td>
                </tr>
                <tr className="border-b border-border/60">
                  <td className="py-2 pr-3">Google（米国、Google LLC）</td>
                  <td className="py-2 pr-3">アクセス解析（Googleアナリティクス）</td>
                  <td className="py-2">
                    <a href="#analytics" className={linkClass}>
                      7.
                    </a>
                    の情報
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <p>
            値下がり通知のメールアドレスは、メールの送信を任せるResendの運営会社（米国）に提供されます。提供先が講ずる個人情報の保護の措置は、
            <a href="https://resend.com/legal/privacy-policy" target="_blank" rel="noopener noreferrer" className={linkClass}>
              Resendのプライバシーポリシー（英語）
            </a>
            で公表されています。値下がり通知に登録するときは、この提供に同意していただいたうえで登録を受け付けます。
            米国の個人情報の保護に関する制度は、個人情報保護委員会の
            <a href={PPC_US_REPORT} target="_blank" rel="noopener noreferrer" className={linkClass}>
              外国の制度の調査（アメリカ）
            </a>
            をご覧ください。米国には、日本の個人情報保護法に相当する、国全体の包括的な法律はありません（州ごと・分野ごとの法律があります）。
          </p>
          <p>各事業者の個人情報の扱いは、それぞれのプライバシーポリシーで公表されています。</p>
        </Section>

        <Section index={6}>
          <p>
            当サイトは、Google LLCのアクセス解析ツール「Googleアナリティクス」を使っています。当サイトのページを開くと、利用者のブラウザから、次の情報がGoogleに送信されます（電気通信事業法の外部送信に関する公表）。
          </p>
          <ul className="list-disc space-y-1 pl-5">
            <li>送信先：Google LLC</li>
            <li>
              送信される情報：閲覧したページのURLとタイトル、参照元のページ、閲覧の日時、ブラウザ・端末・OSの種類、画面の大きさ、言語の設定、IPアドレス（通信の仕組み上、送信されます）、Cookieなどに保存される識別子、サイト内での操作（ショップへのリンクのクリック、値下がり通知の登録など）
            </li>
            <li>利用目的：サイトの利用状況の把握と改善</li>
          </ul>
          <p>
            当サイトは、メールアドレスやお名前などのご入力の内容を、Googleアナリティクスに送らないようにしています。通知の停止のページでは、Googleアナリティクスを動かしません。送信を止めたい場合は、
            <a href="https://tools.google.com/dlpage/gaoptout?hl=ja" target="_blank" rel="noopener noreferrer" className={linkClass}>
              Googleアナリティクス オプトアウト アドオン
            </a>
            を使うか、ブラウザの設定でCookieを無効にしてください。Googleによる情報の扱いは、
            <a
              href="https://policies.google.com/technologies/partner-sites?hl=ja"
              target="_blank"
              rel="noopener noreferrer"
              className={linkClass}
            >
              Googleのサービスを使うサイトでのGoogleによるデータの使用
            </a>
            をご覧ください。
          </p>
        </Section>

        <Section index={7}>
          <p>
            商品の画像は、楽天市場とYahoo!ショッピングの画像サーバーから直接読み込んで表示しています。そのため、画像を表示するときに、利用者のブラウザから各社の画像サーバーに、IPアドレス・ブラウザの種類・表示したページのURLなどの情報が送信されます（送信先：楽天グループ株式会社、LINEヤフー株式会社。目的：商品画像の表示）。
          </p>
        </Section>

        <Section index={8}>
          <p>
            当サイトのショップへのリンクには、アフィリエイトリンク（楽天アフィリエイト、Amazonアソシエイト・プログラム）が含まれます。リンクを押してショップのサイトに移ると、ショップやアフィリエイトの事業者が、Cookieなどを使って、購入が当サイトからの紹介によるものかを記録します。
            この記録はショップ側のサイトで行われ、当サイトがその情報を受け取ることはありません。詳しくは
            <Link href="/disclaimer" className={linkClass}>
              免責事項・アフィリエイトについて
            </Link>
            と、各社のプライバシーポリシーをご覧ください。
          </p>
        </Section>

        <Section index={9}>
          <p>
            お気に入り・最近見た商品・比較リストは、利用者のブラウザの中（ローカルストレージ）に保存し、当サイトのサーバーには保存しません（表示のために、商品の情報をサーバーから読み込みます）。ブラウザの閲覧データを消すと削除されます。
          </p>
        </Section>

        <Section index={10}>
          <ul className="list-disc space-y-1 pl-5">
            <li>値下がり通知：通知を送ってから90日後に削除します。通知を送らないまま登録から1年たった場合も削除します。</li>
            <li>お問い合わせ：運営者が内容を確認（既読に）してから1年後に削除します。</li>
            <li>期限を過ぎた情報は、毎日の自動の処理で削除します。削除した情報は、元に戻せません。</li>
            <li>アクセス解析の情報の保存期間は、Googleアナリティクスの設定に従います。</li>
          </ul>
        </Section>

        <Section index={11}>
          <ul className="list-disc space-y-1 pl-5">
            <li>情報を保存するデータベースと管理画面は、運営者が管理する認証（管理用のトークンとデータベースのパスワード）で保護しています。</li>
            <li>サイトとの通信は、暗号化（HTTPS）しています。</li>
            <li>通知の停止のリンクには、推測できない値を使っています。</li>
            <li>エラーの記録などに、メールアドレスを書き込まないようにしています。</li>
            <li>
              外的環境の把握：情報は米国（オレゴン州）のサーバーに保存しています。米国の制度（
              <a href="#overseas" className={linkClass}>
                6.
              </a>
              ）を把握したうえで、上の措置をとっています。
            </li>
          </ul>
        </Section>

        <Section index={12}>
          <ul className="list-disc space-y-1 pl-5">
            <li>
              値下がり通知は、通知のメールにある「通知の停止・登録の削除」のリンクから、いつでも停止できます。停止すると、登録の情報は削除されます。同じメールアドレスの登録をまとめて削除することもできます。
            </li>
            <li>
              ご自身の情報の開示・訂正・利用の停止・削除をご希望の場合は、
              <Link href="/contact" className={linkClass}>
                お問い合わせフォーム
              </Link>
              からご連絡ください。ご本人であることを確認したうえで、法令に従い、遅滞なく対応します。ご本人の確認は、ご登録のメールアドレスあてにご連絡するなどの方法で行います。費用はいただきません。
            </li>
          </ul>
        </Section>

        <Section index={13}>
          <p>
            このポリシーは、法令の改正やサイトの機能の変更に合わせて改定することがあります。大切な変更は、このページでお知らせします。
            ご質問・苦情は、
            <Link href="/contact" className={linkClass}>
              お問い合わせフォーム
            </Link>
            で受け付けます。
          </p>
          <p className="text-xs text-foreground/65">2026年10月6日 制定</p>
        </Section>
      </article>
    </div>
  );
}
