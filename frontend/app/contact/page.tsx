import type { Metadata } from "next";
import Link from "next/link";

import ContactForm from "./ContactForm";

export const metadata: Metadata = {
  title: "お問い合わせ",
  description: "PAR.へのお問い合わせはこちらのフォームからお願いします。",
};

export default function ContactPage() {
  return (
    <div className="mx-auto max-w-2xl px-6 py-16 sm:py-24">
      <p className="text-xs font-medium uppercase tracking-[0.3em] text-accent">Contact</p>
      <h1 className="mt-2 font-display text-3xl font-semibold text-foreground">お問い合わせ</h1>
      <p className="mt-4 text-sm leading-relaxed text-foreground/60">
        サイトに関するご質問・ご指摘等は、以下のフォームからお送りください。内容を確認のうえ、必要に応じて対応いたします。
        返信をお約束するものではない点、あらかじめご了承ください。
      </p>
      {/* STEP75 (approval #003): purpose of use above the form. */}
      <p className="mt-3 text-xs leading-relaxed text-foreground/65">
        お名前・メールアドレス・お問い合わせ内容は、お問い合わせへの対応（返信を含む）にのみ使い、既読にしてから1年後に削除します。
        詳しくは
        <Link href="/privacy" className="text-brand underline">
          プライバシーポリシー
        </Link>
        をご覧ください。値下がり通知の停止・削除のご依頼も、このフォームで受け付けます。
      </p>

      <div className="mt-10">
        <ContactForm />
      </div>
    </div>
  );
}
