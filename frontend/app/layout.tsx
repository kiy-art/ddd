import type { Metadata } from "next";
import { Geist, JetBrains_Mono, Zen_Kaku_Gothic_New } from "next/font/google";
import Link from "next/link";
import Script from "next/script";

import CompareBar from "@/components/CompareBar";
import Logo from "@/components/Logo";
import SiteNav from "@/components/SiteNav";
import { CATEGORIES, CATEGORY_LABELS } from "@/lib/api";
import { GA_MEASUREMENT_ID } from "@/lib/analytics";

import "./globals.css";
import { SITE_URL } from "@/lib/siteUrl";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

// Numbers - prices, %, scores - in a terminal-grade monospace with
// tabular figures (the .font-num utility, globals.css).
const numFont = JetBrains_Mono({
  variable: "--font-num",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

// Japanese text: a refined, slightly geometric gothic that holds up at
// headline sizes (Latin stays in Geist, which comes first in the stack).
// preload: false - CJK fonts ship as many unicode-range slices; only the
// slices for characters actually on the page are downloaded.
const jpFont = Zen_Kaku_Gothic_New({
  variable: "--font-jp",
  subsets: ["latin"],
  weight: ["400", "500", "700"],
  display: "swap",
  preload: false,
});

const SITE_NAME = "PAR.";
const TITLE = "PAR. | AIゴルフ価格インテリジェンス";
const DESCRIPTION =
  "今日、買うべきゴルフ用品をAIが発見。過去30日の価格データを毎日分析し、「今が買い時か」をスコアでお伝えします。";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: TITLE,
    template: `%s | ${SITE_NAME}`,
  },
  description: DESCRIPTION,
  applicationName: SITE_NAME,
  openGraph: {
    type: "website",
    locale: "ja_JP",
    url: SITE_URL,
    siteName: SITE_NAME,
    title: TITLE,
    description: DESCRIPTION,
  },
  twitter: {
    card: "summary_large_image",
    title: TITLE,
    description: DESCRIPTION,
  },
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="ja"
      className={`${geistSans.variable} ${numFont.variable} ${jpFont.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col bg-background text-foreground">
        {GA_MEASUREMENT_ID && (
          <>
            <Script src={`https://www.googletagmanager.com/gtag/js?id=${GA_MEASUREMENT_ID}`} strategy="afterInteractive" />
            <Script id="ga4-init" strategy="afterInteractive">
              {`
                window.dataLayer = window.dataLayer || [];
                function gtag(){dataLayer.push(arguments);}
                gtag('js', new Date());
                gtag('config', '${GA_MEASUREMENT_ID}');
              `}
            </Script>
          </>
        )}
        <SiteNav>
          <main className="flex-1">{children}</main>

          <footer className="border-t border-border bg-background px-6 py-14 text-sm text-foreground/50">
            <div className="mx-auto flex max-w-5xl flex-col gap-8">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                <Logo className="text-foreground" />
                <nav className="flex flex-wrap gap-x-6 gap-y-2 text-xs">
                  {CATEGORIES.map((c) => (
                    <Link key={c} href={`/category/${c}`} className="hover:text-foreground">
                      {CATEGORY_LABELS[c]}
                    </Link>
                  ))}
                  <Link href="/deals" className="hover:text-foreground">
                    値下がり中
                  </Link>
                  <Link href="/ranking" className="hover:text-foreground">
                    買い時ランキング
                  </Link>
                  <Link href="/brands" className="hover:text-foreground">
                    ブランド一覧
                  </Link>
                  <Link href="/guides" className="hover:text-foreground">
                    購入ガイド
                  </Link>
                  <Link href="/favorites" className="hover:text-foreground">
                    お気に入り
                  </Link>
                  <Link href="/faq" className="hover:text-foreground">
                    よくある質問
                  </Link>
                  <Link href="/contact" className="hover:text-foreground">
                    お問い合わせ
                  </Link>
                  <Link href="/disclaimer" className="hover:text-foreground">
                    運営者情報・免責事項
                  </Link>
                </nav>
              </div>
              <p className="max-w-2xl text-xs leading-relaxed text-foreground/40">
                本サイトはアフィリエイトプログラムを利用して収益を得ています。価格・在庫は変動する可能性が
                あるため、購入前に販売元サイトで最新情報をご確認ください。
              </p>
              <p className="text-xs text-foreground/30">© {new Date().getFullYear()} {SITE_NAME}</p>
            </div>
          </footer>
        </SiteNav>
        <CompareBar />
      </body>
    </html>
  );
}
