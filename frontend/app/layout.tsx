import type { Metadata } from "next";
import { Fraunces, Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";

import Logo from "@/components/Logo";
import { CATEGORIES, CATEGORY_LABELS } from "@/lib/api";

import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const fraunces = Fraunces({
  variable: "--font-fraunces",
  subsets: ["latin"],
  axes: ["opsz", "SOFT", "WONK"],
});

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";
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
      className={`${geistSans.variable} ${geistMono.variable} ${fraunces.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col bg-background text-foreground">
        <header className="sticky top-0 z-20 border-b border-border/70 bg-background/85 backdrop-blur-md">
          <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-6 py-4">
            <Link href="/" className="text-foreground transition-opacity hover:opacity-70">
              <Logo />
            </Link>
            <nav className="flex flex-wrap items-center gap-1 text-sm text-foreground/60">
              {CATEGORIES.map((c) => (
                <Link
                  key={c}
                  href={`/category/${c}`}
                  className="rounded-full px-3 py-1.5 transition-colors hover:bg-foreground/5 hover:text-foreground"
                >
                  {CATEGORY_LABELS[c]}
                </Link>
              ))}
              <Link
                href="/admin"
                className="ml-2 rounded-full border border-border px-3.5 py-1.5 text-foreground/70 transition-colors hover:border-foreground/30 hover:text-foreground"
              >
                管理画面
              </Link>
            </nav>
          </div>
        </header>

        <main className="flex-1">{children}</main>

        <footer className="border-t border-border bg-background px-6 py-14 text-sm text-foreground/50">
          <div className="mx-auto flex max-w-7xl flex-col gap-8">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
              <Logo className="text-foreground" />
              <nav className="flex flex-wrap gap-x-6 gap-y-2 text-xs">
                {CATEGORIES.map((c) => (
                  <Link key={c} href={`/category/${c}`} className="hover:text-foreground">
                    {CATEGORY_LABELS[c]}
                  </Link>
                ))}
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
      </body>
    </html>
  );
}
