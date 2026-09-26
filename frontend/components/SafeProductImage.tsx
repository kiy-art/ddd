"use client";

import Image from "next/image";
import { useState } from "react";

import ProductImagePlaceholder from "@/components/ProductImagePlaceholder";
import { normalizeImageUrl } from "@/lib/imageUrl";

// Every product photo on the site goes through here. The parent box must be
// `relative` with a size (the photo uses `fill`).
//
// `unoptimized`: photos are hotlinked from Rakuten/Yahoo and from any URL
// entered in /admin, and the frontend runs on Render's free instance -
// routing every photo through Next's optimizer would add CPU/memory load
// there and would reject any admin-entered host not in remotePatterns.
// Serving the (already web-sized) CDN image as-is avoids both.
export default function SafeProductImage({
  src,
  alt,
  category,
  className,
  compact = false,
}: {
  src: string | null | undefined;
  alt: string;
  category: string;
  className?: string;
  compact?: boolean;
}) {
  const url = normalizeImageUrl(src);
  // Keyed by URL rather than a bare boolean, so a different photo (e.g. a
  // product edited in /admin, or client-side navigation reusing this
  // component) gets a fresh attempt instead of inheriting the old failure.
  const [failedUrl, setFailedUrl] = useState<string | null>(null);

  if (!url || failedUrl === url) {
    return <ProductImagePlaceholder category={category} compact={compact} />;
  }

  return (
    <Image
      src={url}
      alt={alt}
      fill
      unoptimized
      // Some shop/maker image servers refuse hotlinked requests that carry
      // a third-party Referer; sending none gets the image served normally.
      referrerPolicy="no-referrer"
      className={className}
      onError={() => setFailedUrl(url)}
    />
  );
}
