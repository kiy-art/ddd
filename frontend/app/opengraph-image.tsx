import { ImageResponse } from "next/og";

import { getProducts } from "@/lib/api";
import { CollectionCard, OG_SIZE, THIN_DATA_DAYS, fetchImageDataUri, withTimeout } from "@/lib/og";

export const alt = "PAR. 型落ちクラブ、買うのは今か、待つか。";
export const size = OG_SIZE;
export const contentType = "image/png";

// Default share card (home and any page without its own image).
// 2026-10-20: was text only with the old "AIが発見" copy; now the site concept
// (2026-10-17) plus photos of today's strongest real buy signals.
export default async function Image() {
  const products = (await withTimeout(getProducts({ limit: 200 }))) ?? [];
  const ranked = products
    .filter((p) => p.image_url && p.history_span_days >= THIN_DATA_DAYS && p.buy_signal_score !== null)
    .sort((a, b) => (b.buy_signal_score ?? 0) - (a.buy_signal_score ?? 0));
  const photos = (
    await Promise.all(ranked.slice(0, 4).map((p) => fetchImageDataUri(p.image_url)))
  ).filter((src): src is string => src !== null);

  return new ImageResponse(
    (
      <CollectionCard
        eyebrow="GOLF PRICE ANALYTICS"
        title={"型落ちクラブ、\n買うのは今か、\n待つか。"}
        subtitle="価格の記録から、今日の買い時の目安をお伝えします"
        photos={photos}
        footerRight="価格推移・ショップ別価格・買い時判定"
      />
    ),
    { ...size }
  );
}

// Re-render at most hourly: the photos follow the daily price update.
export const revalidate = 3600;
