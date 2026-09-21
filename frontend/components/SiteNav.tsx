"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import Logo from "@/components/Logo";
import { CATEGORIES, CATEGORY_LABELS } from "@/lib/api";

const NAV_LINKS = [
  ...CATEGORIES.map((c) => ({ href: `/category/${c}`, label: CATEGORY_LABELS[c] })),
  { href: "/deals", label: "値下がり中" },
  { href: "/ranking", label: "買い時ランキング" },
  { href: "/brands", label: "ブランド一覧" },
  { href: "/guides", label: "購入ガイド" },
];

function NavLinks({ pathname, onNavigate }: { pathname: string; onNavigate?: () => void }) {
  return (
    <nav className="flex flex-col gap-1">
      {NAV_LINKS.map((link) => {
        const active = pathname === link.href || pathname.startsWith(`${link.href}/`);
        return (
          <Link
            key={link.href}
            href={link.href}
            onClick={onNavigate}
            className={`rounded-lg px-3 py-2 text-sm transition-colors ${
              active
                ? "bg-foreground/8 font-semibold text-foreground"
                : "text-foreground/60 hover:bg-foreground/5 hover:text-foreground"
            }`}
          >
            {link.label}
          </Link>
        );
      })}
    </nav>
  );
}

export default function SiteNav({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="flex min-h-full flex-1 flex-col md:flex-row">
      {/* Desktop sidebar */}
      <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col overflow-y-auto border-r border-border/70 bg-background md:flex">
        <Link href="/" className="px-6 pb-2 pt-6 text-foreground transition-opacity hover:opacity-70">
          <Logo />
        </Link>
        <div className="flex-1 px-4 py-4">
          <NavLinks pathname={pathname} />
        </div>
        <div className="flex flex-col gap-2 border-t border-border/70 px-4 py-4 text-xs text-foreground/45">
          <Link href="/faq" className="hover:text-foreground">
            よくある質問
          </Link>
          <Link href="/disclaimer" className="hover:text-foreground">
            運営者情報・免責事項
          </Link>
          <Link href="/admin" className="hover:text-foreground">
            管理画面
          </Link>
        </div>
      </aside>

      {/* Mobile top bar */}
      <header className="sticky top-0 z-20 flex items-center justify-between border-b border-border/70 bg-background/90 px-4 py-3 backdrop-blur-md md:hidden">
        <Link href="/" className="text-foreground">
          <Logo />
        </Link>
        <button
          type="button"
          onClick={() => setMobileOpen(true)}
          aria-label="メニューを開く"
          className="rounded-lg p-2 text-foreground/70 hover:bg-foreground/5"
        >
          <svg viewBox="0 0 24 24" fill="none" className="h-6 w-6" aria-hidden="true">
            <path
              d="M4 6h16M4 12h16M4 18h16"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
            />
          </svg>
        </button>
      </header>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-30 md:hidden">
          <div
            className="absolute inset-0 bg-black/40"
            onClick={() => setMobileOpen(false)}
            aria-hidden="true"
          />
          <div className="absolute left-0 top-0 flex h-full w-72 max-w-[80vw] flex-col bg-background px-6 py-6 shadow-xl">
            <div className="mb-6 flex items-center justify-between">
              <Logo />
              <button
                type="button"
                onClick={() => setMobileOpen(false)}
                aria-label="メニューを閉じる"
                className="rounded-lg p-2 text-foreground/70 hover:bg-foreground/5"
              >
                <svg viewBox="0 0 24 24" fill="none" className="h-6 w-6" aria-hidden="true">
                  <path
                    d="M6 6l12 12M18 6L6 18"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                  />
                </svg>
              </button>
            </div>
            <NavLinks pathname={pathname} onNavigate={() => setMobileOpen(false)} />
            <div className="mt-auto flex flex-col gap-2 border-t border-border/70 pt-4 text-xs text-foreground/45">
              <Link href="/faq" onClick={() => setMobileOpen(false)} className="hover:text-foreground">
                よくある質問
              </Link>
              <Link href="/disclaimer" onClick={() => setMobileOpen(false)} className="hover:text-foreground">
                運営者情報・免責事項
              </Link>
              <Link href="/admin" onClick={() => setMobileOpen(false)} className="hover:text-foreground">
                管理画面
              </Link>
            </div>
          </div>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">{children}</div>
    </div>
  );
}
