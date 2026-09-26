"use client";

import { normalizeImageUrl } from "@/lib/imageUrl";

// A scattered backdrop of this site's own tracked product photography
// (the same hotlinked retailer images already shown on every ProductCard/
// product page, with the same attribution norms - see the "画像提供" note
// on app/products/[slug]/page.tsx) - never stock photography or an image
// pulled from elsewhere on the web. Purely decorative: hidden from screen
// readers, faded low enough that it never competes with foreground text,
// and masked so it never overlaps the copy on the left.

interface Slot {
  top: string;
  left: string;
  size: number;
  rotate: number;
  opacity: number;
}

// Fixed, hand-placed positions (not random) so the layout is stable across
// server/client renders and never jumps on hydration.
const SLOTS: Slot[] = [
  { top: "4%", left: "58%", size: 132, rotate: -6, opacity: 0.85 },
  { top: "42%", left: "78%", size: 104, rotate: 8, opacity: 0.7 },
  { top: "58%", left: "48%", size: 92, rotate: -10, opacity: 0.55 },
  { top: "10%", left: "86%", size: 88, rotate: 5, opacity: 0.6 },
  { top: "68%", left: "68%", size: 76, rotate: 12, opacity: 0.45 },
  { top: "26%", left: "34%", size: 68, rotate: -8, opacity: 0.35 },
];

function hideTile(img: HTMLImageElement) {
  img.parentElement?.style.setProperty("display", "none");
}

export default function ProductPhotoCollage({ images }: { images: (string | null | undefined)[] }) {
  const usable = images
    .map(normalizeImageUrl)
    .filter((src): src is string => src !== null)
    .slice(0, SLOTS.length);
  if (usable.length === 0) return null;

  return (
    <div
      aria-hidden="true"
      className="pointer-events-none absolute inset-0 overflow-hidden"
      style={{
        maskImage: "linear-gradient(115deg, transparent 0%, transparent 22%, black 48%, black 100%)",
        WebkitMaskImage: "linear-gradient(115deg, transparent 0%, transparent 22%, black 48%, black 100%)",
      }}
    >
      {usable.map((src, i) => {
        const slot = SLOTS[i];
        return (
          <div
            key={src + i}
            className="absolute rounded-2xl bg-card shadow-[0_20px_40px_-20px_rgba(20,19,15,0.25)]"
            style={{
              top: slot.top,
              left: slot.left,
              width: slot.size,
              height: slot.size,
              transform: `rotate(${slot.rotate}deg)`,
              opacity: slot.opacity,
            }}
          >
            {/* eslint-disable-next-line @next/next/no-img-element -- decorative, best-effort background element (not core content), doesn't need next/image's optimization/fallback machinery */}
            <img
              src={src}
              alt=""
              referrerPolicy="no-referrer"
              className="h-full w-full rounded-2xl object-contain p-3"
              onError={(e) => hideTile(e.currentTarget)}
              // A photo that failed BEFORE React hydrated never fires onError
              // (the event is gone by the time the handler attaches) - check
              // once on mount so a dead photo can't linger as a broken tile.
              ref={(img) => {
                if (img && img.complete && img.naturalWidth === 0) hideTile(img);
              }}
            />
          </div>
        );
      })}
    </div>
  );
}
