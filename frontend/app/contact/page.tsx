import type { Metadata } from "next";

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

      <div className="mt-10">
        <ContactForm />
      </div>
    </div>
  );
}
