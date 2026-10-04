/**
 * STEP74: the one PR disclosure line for any page that links to shops
 * (ステマ規制: an advertisement must be recognisable as one). Placed before
 * the page's first shop link - e.g. above the first product-card list,
 * whose cards carry a "楽天市場で見る" button. Server component, readable
 * contrast (foreground/65 on the page background, 12px).
 */
export default function PrNotice({ className = "" }: { className?: string }) {
  return (
    <p className={`flex items-start gap-2 text-xs leading-relaxed text-foreground/65 ${className}`}>
      <span className="mt-px shrink-0 rounded border border-foreground/30 px-1.5 text-[11px] font-semibold leading-5 text-foreground/70">
        PR
      </span>
      <span>
        本ページはプロモーション（アフィリエイト広告）を含みます。リンク経由の購入により当サイトが紹介料を受け取ることがあります。
      </span>
    </p>
  );
}
