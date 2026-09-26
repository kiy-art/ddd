import { ImageResponse } from "next/og";

import { CATEGORY_LABELS, getCategoryProducts } from "@/lib/api";
import {
  CollectionCard,
  OG_API_TIMEOUT_MS,
  OG_SIZE,
  THIN_DATA_DAYS,
  fetchImageDataUri,
  withTimeout,
} from "@/lib/og";

export const alt = "PAR. カテゴリ別の価格推移と買い時判定";
export const size = OG_SIZE;
export const contentType = "image/png";

// Without this file the category page had no og:image at all: its own
// generateMetadata openGraph block replaces the root segment's, so the
// root opengraph-image was never emitted here and X showed a grey card.
export default async function Image({ params }: { params: Promise<{ category: string }> }) {
  const { category } = await params;
  const label = CATEGORY_LABELS[category] ?? "ゴルフ用品";

  const products =
    (await withTimeout(getCategoryProducts(category, { signal: AbortSignal.timeout(OG_API_TIMEOUT_MS) }))) ?? [];
  // Photos of the category's strongest real buy signals first (same
  // "enough history to trust it" bar as the rest of the site).
  const ranked = [...products]
    .filter((p) => p.image_url)
    .sort((a, b) => {
      const sa = a.history_span_days >= THIN_DATA_DAYS ? (a.buy_signal_score ?? -1) : -1;
      const sb = b.history_span_days >= THIN_DATA_DAYS ? (b.buy_signal_score ?? -1) : -1;
      return sb - sa;
    });
  const photos = (await Promise.all(ranked.slice(0, 4).map((p) => fetchImageDataUri(p.image_url)))).filter(
    (src): src is string => src !== null
  );

  return new ImageResponse(
    (
      <CollectionCard
        eyebrow="TODAY'S DEALS"
        title={`今日の${label}\nお買い得`}
        subtitle={products.length > 0 ? `${products.length}商品の価格を毎日追跡。今が買い時かをスコアで判定` : "価格推移と買い時判定を毎日更新"}
        photos={photos}
        footerRight="相場推移・ショップ別価格・買い時判定"
      />
    ),
    { ...size }
  );
}
