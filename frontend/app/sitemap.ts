import type { MetadataRoute } from "next";

import { CATEGORIES, getProducts } from "@/lib/api";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const staticEntries: MetadataRoute.Sitemap = [
    { url: SITE_URL, changeFrequency: "daily", priority: 1 },
    { url: `${SITE_URL}/disclaimer`, changeFrequency: "yearly", priority: 0.2 },
    ...CATEGORIES.map((category) => ({
      url: `${SITE_URL}/category/${category}`,
      changeFrequency: "daily" as const,
      priority: 0.7,
    })),
  ];

  try {
    const products = await getProducts();
    const productEntries: MetadataRoute.Sitemap = products.map((product) => ({
      url: `${SITE_URL}/products/${product.slug}`,
      lastModified: product.updated_at,
      changeFrequency: "daily",
      priority: 0.8,
    }));
    return [...staticEntries, ...productEntries];
  } catch {
    return staticEntries;
  }
}
