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
      <body className="flex min-h-full flex-col bg-zinc-50 text-zinc-900 dark:bg-zinc-950 dark:text-zinc-50">
        <header className="border-b border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900">
          <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-4 py-4">
            <Link href="/" className="text-lg font-bold">
              ⛳ ゴルフ買い時ナビ
            </Link>
            <nav className="flex flex-wrap gap-4 text-sm text-zinc-600 dark:text-zinc-300">
              {CATEGORIES.map((c) => (
                <Link key={c} href={`/category/${c}`} className="hover:text-zinc-900 dark:hover:text-white">
                  {CATEGORY_LABELS[c]}
                </Link>
              ))}
              <Link href="/admin" className="hover:text-zinc-900 dark:hover:text-white">
                管理画面
              </Link>
            </nav>
          </div>
        </header>
        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">{children}</main>
        <footer className="flex flex-col items-center gap-2 border-t border-zinc-200 px-4 py-6 text-center text-xs text-zinc-400 dark:border-zinc-800">
          <p>
            本サイトはアフィリエイトプログラムを利用して収益を得ています。価格・在庫は変動する可能性があるため、購入前に販売元サイトでご確認ください。
          </p>
          <Link href="/disclaimer" className="underline hover:text-zinc-600 dark:hover:text-zinc-300">
            運営者情報・免責事項
          </Link>
        </footer>
      </body>
    </html>
  );
}
