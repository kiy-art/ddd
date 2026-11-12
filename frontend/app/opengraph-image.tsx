import { ImageResponse } from "next/og";

import { getProducts } from "@/lib/api";
import { CollectionCard, OG_SIZE, THIN_DATA_DAYS, fetchImageDataUri, ogFonts, withTimeout } from "@/lib/og";

export const alt = "PAR. そのクラブ、定価で買ってない？";
export const size = OG_SIZE;
export const contentType = "image/png";

// Default share card (home and any page without its own image).
// 2026-11-12: "値下がり速報" look. The two photos are the clubs whose price
// is furthest BELOW their own 30-day average right now (a recorded fact,
// shown as a red "-NN%" badge with the basis "30日平均比" on the badge).
const CLUB_CATEGORIES = new Set(["driver", "iron", "wedge", "putter", "fairway", "utility"]);

export default async function Image() {
  const products = (await withTimeout(getProducts({ limit: 200 }))) ?? [];
  const ranked = products
    .filter(
      (p) =>
        p.image_url &&
        CLUB_CATEGORIES.has(p.category) &&
        p.history_span_days >= THIN_DATA_DAYS &&
        p.price_change_percent !== null &&
        p.price_change_percent <= -5
    )
    .sort((a, b) => (a.price_change_percent ?? 0) - (b.price_change_percent ?? 0));

  // Keep photo and badge together: a product whose photo can't be fetched is skipped.
  const picked: Array<{ src: string; badge: string }> = [];
  for (const p of ranked.slice(0, 5)) {
    if (picked.length === 2) break;
    const src = await fetchImageDataUri(p.image_url);
    if (src) picked.push({ src, badge: `${Math.round(p.price_change_percent ?? 0)}%` });
  }

  const title = "そのクラブ、\n定価で\n買ってない？";
  const subtitle = "毎日値段を記録。下がった瞬間がわかる";
  const cta = "今日の値下がりを見る";
  const footerRight = "価格推移・ショップ別価格・買い時判定";
  const fonts = await ogFonts(["値下がり速報", title, subtitle, cta, footerRight, "30日平均比"]);

  return new ImageResponse(
    (
      <CollectionCard
        eyebrow="値下がり速報"
        title={title}
        subtitle={subtitle}
        photos={picked.map((p) => p.src)}
        badges={picked.map((p) => p.badge)}
        badgeCaption="30日平均比"
        cta={cta}
        footerRight={footerRight}
      />
    ),
    { ...size, fonts }
  );
}

// Re-render at most hourly: the photos follow the daily price update.
export const revalidate = 3600;
