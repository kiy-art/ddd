"use client";

import { useCallback, useSyncExternalStore } from "react";

import { isFavorite, subscribe, toggleFavorite } from "@/lib/favorites";

const getServerSnapshot = () => false;

export default function FavoriteButton({ slug, className }: { slug: string; className?: string }) {
  const getSnapshot = useCallback(() => isFavorite(slug), [slug]);
  const favorited = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  return (
    <button
      type="button"
      onClick={(e) => {
        e.preventDefault();
        e.stopPropagation();
        toggleFavorite(slug);
      }}
      aria-label={favorited ? "お気に入りから削除" : "お気に入りに追加"}
      aria-pressed={favorited}
      className={className}
    >
      <svg
        viewBox="0 0 24 24"
        className="h-5 w-5"
        fill={favorited ? "currentColor" : "none"}
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <path
          d="M12 21s-7.5-4.6-10-9.1C.6 8.4 2 4.8 5.5 4c2-.5 4 .3 5 2 1-1.7 3-2.5 5-2 3.5.8 4.9 4.4 3.5 7.9C19.5 16.4 12 21 12 21z"
          strokeLinejoin="round"
          strokeLinecap="round"
        />
      </svg>
    </button>
  );
}
