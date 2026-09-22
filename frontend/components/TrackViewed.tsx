"use client";

import { useEffect } from "react";

import { trackViewed } from "@/lib/recentlyViewed";

/** Records a product-detail visit to localStorage for the /favorites page's
 * "recently viewed" section. Renders nothing. */
export default function TrackViewed({ slug }: { slug: string }) {
  useEffect(() => {
    trackViewed(slug);
  }, [slug]);

  return null;
}
