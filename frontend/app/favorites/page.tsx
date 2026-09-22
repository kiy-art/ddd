import type { Metadata } from "next";

import FavoritesClient from "./FavoritesClient";

export const metadata: Metadata = {
  title: "お気に入り",
  robots: { index: false }, // per-browser localStorage content, nothing here is the same for two visitors
};

export default function FavoritesPage() {
  return <FavoritesClient />;
}
