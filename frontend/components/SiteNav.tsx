"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import Logo from "@/components/Logo";
import { CATEGORIES, CATEGORY_LABELS } from "@/lib/api";

const NAV_LINKS = [
  ...CATEGORIES.map((c) => ({ href: `/category/${c}`, label: CATEGORY_LABELS[c] })),
  { href: "/finder", label: "クラブ診断" },
  { href: "/popular", label: "人気ランキング" },
  { href: "/deals", label: "値下がり中" },
  { href: "/ranking", label: "買い時ランキング" },
  { href: "/brands", label: "ブランド一覧" },
  { href: "/guides", label: "購入ガイド" },
];

function SearchForm({ className }: { className?: string }) {
  return (
    <form action="/search" method="GET" className={className}>
      <input
        type="text"
        name="q"
        placeholder="商品を検索"
        aria-label="商品を検索"
        className="w-full rounded-full border border-border bg-card px-4 py-2 text-sm text-foreground outline-none focus:border-brand"
      />
    </form>
  );
}

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
            aria-current={active ? "page" : undefined}
            className={`relative rounded-lg px-3 py-2 text-sm transition-colors ${
              active
                ? "bg-foreground/[0.06] font-semibold text-foreground before:absolute before:inset-y-2 before:left-0 before:w-[3px] before:rounded-full before:bg-brand-light before:shadow-[0_0_10px_rgba(var(--glow),0.7)]"
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

const TAB_BAR_ITEMS = [
  {
    href: "/",
    label: "ホーム",
    icon: (
      <path d="M4 11 L12 4 L20 11 M6 10 V20 H18 V10" strokeLinecap="round" strokeLinejoin="round" />
    ),
  },
  {
    href: "/deals",
    label: "値下がり",
    icon: <path d="M4 6 L12 15 L16 11 L20 15 M14 15 H20 V9" strokeLinecap="round" strokeLinejoin="round" />,
  },
  {
    href: "/ranking",
    label: "買い時",
    icon: (
      <>
        <path d="M7 20 H17 M12 15 V20" strokeLinecap="round" />
        <path d="M6 4 H18 V9 C18 12.5 15.3 15 12 15 C8.7 15 6 12.5 6 9 Z" strokeLinejoin="round" />
      </>
    ),
  },
] as const;

function MobileTabBar({ pathname, onMore, moreOpen }: { pathname: string; onMore: () => void; moreOpen: boolean }) {
  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-20 flex border-t border-border/80 bg-background/95 pb-[env(safe-area-inset-bottom)] shadow-[0_-8px_24px_-18px_rgba(6,16,12,0.35)] backdrop-blur-xl md:hidden"
      aria-label="主要ナビゲーション"
    >
      {TAB_BAR_ITEMS.map((item) => {
        const active = pathname === item.href || (item.href !== "/" && pathname.startsWith(`${item.href}/`));
        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={active ? "page" : undefined}
            className={`tap relative flex flex-1 flex-col items-center gap-1 py-2.5 text-[10px] font-semibold ${
              active ? "text-brand" : "text-foreground/45"
            }`}
          >
            {/* active indicator: a small emerald bar with a soft glow */}
            <span
              aria-hidden="true"
              className={`absolute top-0 h-[3px] rounded-full bg-brand-light transition-all duration-300 ${
                active ? "w-7 opacity-100 shadow-[0_0_10px_rgba(var(--glow),0.8)]" : "w-0 opacity-0"
              }`}
            />
            <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
              {item.icon}
            </svg>
            {item.label}
          </Link>
        );
      })}
      <button
        type="button"
        onClick={onMore}
        aria-expanded={moreOpen}
        aria-haspopup="dialog"
        className={`tap relative flex flex-1 flex-col items-center gap-1 py-2.5 text-[10px] font-semibold ${
          moreOpen ? "text-brand" : "text-foreground/45"
        }`}
      >
        <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
          <circle cx="5" cy="12" r="1.4" fill="currentColor" stroke="none" />
          <circle cx="12" cy="12" r="1.4" fill="currentColor" stroke="none" />
          <circle cx="19" cy="12" r="1.4" fill="currentColor" stroke="none" />
        </svg>
        もっと
      </button>
    </nav>
  );
}

const SHEET_FOOTER_LINKS = [
  { href: "/favorites", label: "お気に入り" },
  { href: "/faq", label: "よくある質問" },
  { href: "/contact", label: "お問い合わせ" },
  { href: "/disclaimer", label: "運営者情報・免責事項" },
  { href: "/admin", label: "管理画面" },
];

// Mobile menu as an app-style bottom sheet (thumb-reachable, slides up with
// a spring-like ease, slides back down on close - globals.css .sheet-*).
function MobileSheet({
  state,
  pathname,
  onClose,
}: {
  state: "open" | "closing";
  pathname: string;
  onClose: () => void;
}) {
  return (
    <div className="fixed inset-0 z-40 md:hidden" role="dialog" aria-modal="true" aria-label="メニュー">
      <div
        className={`absolute inset-0 bg-[#06100c]/50 backdrop-blur-[2px] ${state === "open" ? "backdrop-enter" : "backdrop-exit"}`}
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        className={`absolute inset-x-0 bottom-0 flex max-h-[85vh] flex-col rounded-t-3xl border-t border-border-strong bg-background pb-[calc(env(safe-area-inset-bottom)+1rem)] shadow-[0_-24px_60px_-20px_rgba(6,16,12,0.5)] ${
          state === "open" ? "sheet-enter" : "sheet-exit"
        }`}
      >
        <div className="flex items-center justify-between px-6 pb-2 pt-3">
          <span aria-hidden="true" className="absolute left-1/2 top-2 h-1 w-10 -translate-x-1/2 rounded-full bg-foreground/15" />
          <span className="mt-3 text-xs font-semibold uppercase tracking-[0.25em] text-foreground/40">Menu</span>
          <button
            type="button"
            onClick={onClose}
            aria-label="メニューを閉じる"
            className="tap mt-3 rounded-full p-2 text-foreground/60 hover:bg-foreground/5"
          >
            <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" aria-hidden="true">
              <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
            </svg>
          </button>
        </div>
        <div className="overflow-y-auto px-5">
          <SearchForm className="mb-4" />
          <nav className="grid grid-cols-2 gap-2">
            {NAV_LINKS.map((link) => {
              const active = pathname === link.href || pathname.startsWith(`${link.href}/`);
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  onClick={onClose}
                  aria-current={active ? "page" : undefined}
                  className={`tap rounded-2xl border px-4 py-3 text-sm font-semibold ${
                    active
                      ? "border-brand/40 bg-brand/[0.07] text-brand"
                      : "border-border bg-card text-foreground/80 hover:border-border-strong"
                  }`}
                >
                  {link.label}
                </Link>
              );
            })}
          </nav>
          <div className="mt-5 flex flex-wrap gap-x-5 gap-y-2 border-t border-border/70 pt-4 text-xs text-foreground/45">
            {SHEET_FOOTER_LINKS.map((link) => (
              <Link key={link.href} href={link.href} onClick={onClose} className="py-1 hover:text-foreground">
                {link.label}
              </Link>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function SiteNav({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [sheet, setSheet] = useState<"closed" | "open" | "closing">("closed");
  const openSheet = useCallback(() => setSheet("open"), []);
  const closeSheet = useCallback(() => {
    setSheet((current) => (current === "open" ? "closing" : current));
    window.setTimeout(() => setSheet("closed"), 240);
  }, []);

  // While the sheet is open: Esc closes it and the page behind doesn't scroll.
  useEffect(() => {
    if (sheet !== "open") return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") closeSheet();
    };
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", onKey);
    };
  }, [sheet, closeSheet]);

  return (
    <div className="flex min-h-full flex-1 flex-col md:flex-row">
      {/* Desktop sidebar */}
      <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col overflow-y-auto border-r border-border/70 bg-background md:flex">
        <Link href="/" className="px-6 pb-2 pt-6 text-foreground transition-opacity hover:opacity-70">
          <Logo />
        </Link>
        <div className="flex-1 px-4 py-4">
          <SearchForm className="mb-4" />
          <NavLinks pathname={pathname} />
        </div>
        <div className="flex flex-col gap-2 border-t border-border/70 px-4 py-4 text-xs text-foreground/45">
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
          onClick={openSheet}
          aria-label="メニューを開く"
          aria-expanded={sheet === "open"}
          aria-haspopup="dialog"
          className="tap rounded-lg p-2 text-foreground/70 hover:bg-foreground/5"
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

      {sheet !== "closed" && <MobileSheet state={sheet} pathname={pathname} onClose={closeSheet} />}

      <div className="flex min-w-0 flex-1 flex-col pb-16 md:pb-0">{children}</div>

      <MobileTabBar pathname={pathname} onMore={openSheet} moreOpen={sheet === "open"} />
    </div>
  );
}
