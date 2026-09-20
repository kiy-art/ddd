import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";

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

export const metadata: Metadata = {
  title: "ゴルフ買い時ナビ",
  description: "ゴルフ用品の価格推移をもとに、今買う価値がある商品をAIが判定して紹介します。",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="ja"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col bg-background text-foreground">
        <header className="sticky top-0 z-10 border-b border-brand-dark/20 bg-brand text-white shadow-sm">
          <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-4 py-4">
            <Link href="/" className="flex items-center gap-2 text-lg font-bold tracking-tight">
              <span className="text-2xl">⛳</span>
              ゴルフ買い時ナビ
            </Link>
            <nav className="flex flex-wrap items-center gap-1 text-sm text-white/85">
              {CATEGORIES.map((c) => (
                <Link
                  key={c}
                  href={`/category/${c}`}
                  className="rounded-md px-2.5 py-1.5 transition-colors hover:bg-white/10 hover:text-white"
                >
                  {CATEGORY_LABELS[c]}
                </Link>
              ))}
              <Link
                href="/admin"
                className="ml-1 rounded-md border border-white/25 px-2.5 py-1.5 transition-colors hover:bg-white/10 hover:text-white"
              >
                管理画面
              </Link>
            </nav>
          </div>
        </header>

        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">{children}</main>

        <footer className="border-t border-border bg-card px-4 py-8 text-center text-xs text-foreground/50">
          <div className="mx-auto flex max-w-6xl flex-col items-center gap-2">
            <p className="max-w-2xl">
              本サイトはアフィリエイトプログラムを利用して収益を得ています。価格・在庫は変動する可能性があるため、購入前に販売元サイトでご確認ください。
            </p>
            <Link href="/disclaimer" className="font-medium text-brand underline underline-offset-2 hover:text-brand-dark dark:text-brand-light">
              運営者情報・免責事項
            </Link>
            <p className="mt-2 text-foreground/30">© {new Date().getFullYear()} ゴルフ買い時ナビ</p>
          </div>
        </footer>
      </body>
    </html>
  );
}
