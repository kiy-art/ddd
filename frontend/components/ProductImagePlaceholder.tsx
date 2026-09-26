import CategoryIcon from "@/components/CategoryIcon";
import { LogoMark } from "@/components/Logo";

// The site-wide "NO IMAGE" stand-in: shown when a product has no photo, its
// URL isn't usable (see lib/imageUrl.ts), or the photo fails to load. Pure
// SVG/CSS - no image request of its own, so it can never break too. Fills
// whatever box it's placed in (the same boxes SafeProductImage fills).
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
      className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-background"
    >
      <div className={compact ? "h-3/5 w-3/5" : "h-1/2 w-1/2"}>
        <CategoryIcon category={category} />
      </div>
      {!compact && (
        <span className="inline-flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[0.2em] text-foreground/30">
          <LogoMark className="h-3.5 w-3.5" />
          No Image
        </span>
      )}
    </div>
  );
}
