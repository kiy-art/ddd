import type { MetadataRoute } from "next";

import { CATEGORIES, getBrands, getProducts } from "@/lib/api";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const staticEntries: MetadataRoute.Sitemap = [
    { url: SITE_URL, changeFrequency: "daily", priority: 1 },
    { url: `${SITE_URL}/deals`, changeFrequency: "daily", priority: 0.8 },
    { url: `${SITE_URL}/ranking`, changeFrequency: "daily", priority: 0.8 },
    { url: `${SITE_URL}/brands`, changeFrequency: "weekly", priority: 0.5 },
    { url: `${SITE_URL}/disclaimer`, changeFrequency: "yearly", priority: 0.2 },
    ...CATEGORIES.map((category) => ({
      url: `${SITE_URL}/category/${category}`,
      changeFrequency: "daily" as const,
      priority: 0.7,
    })),
  ];

  let productEntries: MetadataRoute.Sitemap = [];
  try {
    const products = await getProducts();
    productEntries = products.map((product) => ({
      url: `${SITE_URL}/products/${product.slug}`,
      lastModified: product.updated_at,
      changeFrequency: "daily",
      priority: 0.8,
    }));
  } catch {
    productEntries = [];
  }

  let brandEntries: MetadataRoute.Sitemap = [];
  try {
    const brands = await getBrands();
    brandEntries = brands.map((b) => ({
      url: `${SITE_URL}/brand/${encodeURIComponent(b.brand)}`,
      changeFrequency: "daily",
      priority: 0.6,
    }));
  } catch {
    brandEntries = [];
  }

  return [...staticEntries, ...productEntries, ...brandEntries];
}
