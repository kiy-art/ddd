import { ImageResponse } from "next/og";

import { getGuideBySlug } from "@/lib/guides";
import { CollectionCard, OG_SIZE, ogFonts, truncate, withTimeout } from "@/lib/og";

export const alt = "PAR. 購入ガイド";
export const size = OG_SIZE;
export const contentType = "image/png";

// Same gap as the category page: the guide page's own openGraph metadata
// replaced the root image, so guides were shared with no og:image.
export default async function Image({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const guide = await withTimeout(getGuideBySlug(slug));

  const title = truncate(guide?.title ?? "ゴルフ用品の購入ガイド", 36);
  const subtitle = guide ? truncate(guide.description, 60) : null;
  const cta = "続きを読む";
  const footerRight = "実際の価格データに基づく購入ガイド";
  const fonts = await ogFonts(["GUIDE", title, subtitle, cta, footerRight]);

  return new ImageResponse(
    (
      <CollectionCard eyebrow="GUIDE" title={title} subtitle={subtitle} photos={[]} cta={cta} footerRight={footerRight} />
    ),
    { ...size, fonts }
  );
}
