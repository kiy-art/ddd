import type { Metadata } from "next";

import UnsubscribeForm from "./UnsubscribeForm";

// STEP75 (approval #003): the page behind the link in every price-alert
// mail. Opening it only shows what will be stopped (a GET); stopping is
// the button, so a mail client that prefetches links can't stop it.
export const metadata: Metadata = {
  title: "値下がり通知の停止",
  robots: { index: false, follow: false },
  referrer: "no-referrer", // the token is in the URL
};

export default async function UnsubscribePage({ searchParams }: { searchParams: Promise<{ token?: string }> }) {
  const { token } = await searchParams;
  return (
    <div className="mx-auto max-w-xl px-6 py-16 sm:py-24">
      <h1 className="font-display text-2xl font-semibold text-foreground">値下がり通知の停止・登録の削除</h1>
      <div className="mt-8">
        <UnsubscribeForm token={token ?? ""} />
      </div>
    </div>
  );
}
