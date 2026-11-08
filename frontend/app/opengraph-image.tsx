import { ImageResponse } from "next/og";

import { getProducts } from "@/lib/api";
import { CollectionCard, OG_SIZE, THIN_DATA_DAYS, fetchImageDataUri, withTimeout } from "@/lib/og";

export const alt = "PAR. そのクラブ、定価で買ってない？";
export const size = OG_SIZE;
export const contentType = "image/png";

// Default share card (home and any page without its own image).
// 2026-10-20: was text only with the old "AIが発見" copy; now the site concept
// (2026-10-17) plus photos of today's strongest real buy signals.
const CLUB_CATEGORIES = new Set(["driver", "iron", "wedge", "putter", "fairway", "utility"]);

export default async function Image() {
  const products = (await withTimeout(getProducts({ limit: 200 }))) ?? [];
  const ranked = products
    // 2026-11-08: clubs only - balls/gloves made the card read as a ball shop.
    .filter((p) => p.image_url && CLUB_CATEGORIES.has(p.category) && p.history_span_days >= THIN_DATA_DAYS && p.buy_signal_score !== null)
    .sort((a, b) => (b.buy_signal_score ?? 0) - (a.buy_signal_score ?? 0));
  const photos = (
    await Promise.all(ranked.slice(0, 4).map((p) => fetchImageDataUri(p.image_url)))
  ).filter((src): src is string => src !== null);

  return new ImageResponse(
    (
      <CollectionCard
        eyebrow="GOLF PRICE ANALYTICS"
        title={"そのクラブ、\n定価で\n買ってない？"}
        subtitle="毎日値段を記録してるから、下がった瞬間がわかる！"
        photos={photos}
        footerRight="価格推移・ショップ別価格・買い時判定"
      />
    ),
    { ...size }
  );
}

// Re-render at most hourly: the photos follow the daily price update.
export const revalidate = 3600;
