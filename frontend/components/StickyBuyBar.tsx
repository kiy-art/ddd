"use client";

import { useEffect, useState } from "react";

import CtaArrow from "@/components/CtaArrow";
import TrackedCta from "@/components/TrackedCta";

// STEP65 (CRO): a slim buy bar pinned to the bottom of the product page, so
// the cheapest shop is one tap away at any scroll position - the page is
// long (chart, specs, FAQ), and until now the shop buttons were only in two
// places. On a phone it sits just above the tab bar (SiteNav, ~60px).
//
// Hidden while the page's own buy box or store comparison board is on
// screen, so the same button is never shown twice at once. Same price,
// shop and tracking as the buy box (built from lib/shopRows.ts by the page).

const WATCHED_IDS = ["buy-box", "store-comparison"];
const SHORT_LABELS: Record<string, string> = { 楽天市場: "楽天", "Yahoo!ショッピング": "Yahoo!" };

export default function StickyBuyBar({
  href,
  shopLabel,
  price,
  isLowest,
  sponsored,
  productName,
  trackParams,
  productId,
  category,
}: {
  href: string;
  shopLabel: string;
  price: string | null;
  isLowest: boolean;
  sponsored: boolean;
  productName: string;
  trackParams: Record<string, string | number | boolean>;
  productId: number;
  category: string;
}) {
  const [hidden, setHidden] = useState(true);
  // Short shop names so price + button fit one line on a 360px phone.
  const shortLabel = SHORT_LABELS[shopLabel] ?? shopLabel;

  useEffect(() => {
    const targets = WATCHED_IDS.map((id) => document.getElementById(id)).filter(
      (el): el is HTMLElement => el !== null
    );
    // The observer reports every target's initial state right away, so the
    // bar appears as soon as neither box is on screen.
    if (targets.length === 0 || typeof IntersectionObserver === "undefined") return;
    const visible = new Set<Element>();
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) visible.add(entry.target);
          else visible.delete(entry.target);
        }
        setHidden(visible.size > 0);
      },
      { threshold: 0.15 }
    );
    targets.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, []);

  return (
    <div
      aria-hidden={hidden}
      className={`fixed inset-x-0 z-[15] px-3 transition-all duration-300 md:bottom-4 md:px-6 bottom-[calc(3.9rem+env(safe-area-inset-bottom))] ${
        hidden ? "pointer-events-none translate-y-4 opacity-0" : "translate-y-0 opacity-100"
      }`}
    >
      <div className="mx-auto flex max-w-3xl items-center gap-3 rounded-2xl border border-brand/25 bg-white/95 py-2.5 pl-4 pr-2.5 shadow-[0_18px_40px_-18px_rgba(4,120,87,0.55)] backdrop-blur-md">
        <div className="min-w-0 flex-1">
          <p className="hidden truncate text-xs text-foreground/55 sm:block">{productName}</p>
          {price && <p className="font-num text-lg font-semibold leading-tight text-foreground">{price}</p>}
          <p className="truncate text-[11px] font-semibold text-brand">
            {isLowest ? `${shopLabel}が最安` : `${shopLabel}の価格・在庫`}
          </p>
        </div>
        <TrackedCta
          href={href}
          target="_blank"
          rel={sponsored ? "noopener noreferrer sponsored" : "noopener noreferrer"}
          className="btn-shop tap inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-full px-5 py-3 text-sm font-semibold"
          event="cta_click"
          params={trackParams}
          productId={productId}
          category={category}
          placement="product_sticky_bar"
        >
          {shortLabel}で見る
          <CtaArrow className="h-3.5 w-3.5" />
        </TrackedCta>
      </div>
    </div>
  );
}
