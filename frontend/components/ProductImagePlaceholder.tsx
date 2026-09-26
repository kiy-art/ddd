import CategoryIcon from "@/components/CategoryIcon";

// The site-wide "NO IMAGE" stand-in: shown when a product has no photo, its
// URL isn't usable (see lib/imageUrl.ts), or the photo fails to load. Pure
// SVG/CSS - no image request of its own, so it can never break too. Fills
// whatever box it's placed in (the same boxes SafeProductImage fills).
//
// STEP50: a quiet "instrument" look - faint measurement grid, the
// category's line icon inside a hairline frame, and a small mono caption -
// so a missing photo reads as a deliberate state, not a broken page.
export default function ProductImagePlaceholder({
  category,
  compact = false,
}: {
  category: string;
  // Small thumbnails (ranking rows, compare columns) drop the caption.
  compact?: boolean;
}) {
  return (
    <div
      role="img"
      aria-label="商品画像なし"
      className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-background"
      style={{
        backgroundImage:
          "linear-gradient(color-mix(in srgb, var(--foreground) 5%, transparent) 1px, transparent 1px), linear-gradient(90deg, color-mix(in srgb, var(--foreground) 5%, transparent) 1px, transparent 1px)",
        backgroundSize: "20px 20px",
        backgroundPosition: "center",
      }}
    >
      <div
        className={`relative flex items-center justify-center rounded-2xl border border-border-strong bg-card/80 backdrop-blur-sm ${
          compact ? "h-3/5 w-3/5" : "h-2/5 w-2/5 min-h-16 min-w-16"
        }`}
      >
        <div className="h-3/4 w-3/4">
          <CategoryIcon category={category} />
        </div>
      </div>
      {!compact && (
        <span className="font-num text-[10px] font-medium uppercase tracking-[0.3em] text-foreground/35">No Image</span>
      )}
    </div>
  );
}
