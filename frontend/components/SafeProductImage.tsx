"use client";

import Image from "next/image";
import { useState } from "react";

import CategoryIcon from "@/components/CategoryIcon";

export default function SafeProductImage({
  src,
  alt,
  category,
  className,
}: {
  src: string;
  alt: string;
  category: string;
  className?: string;
}) {
  const [failed, setFailed] = useState(false);

  if (failed) {
    return <CategoryIcon category={category} />;
  }

  return (
    <Image
      src={src}
      alt={alt}
      fill
      unoptimized
      className={className}
      onError={() => setFailed(true)}
    />
  );
}
