"use client";

import { trackEvent } from "@/lib/analytics";

export default function TrackedCta({
  href,
  event,
  params,
  className,
  children,
  target,
  rel,
}: {
  href: string;
  event: string;
  params?: Record<string, string | number | boolean>;
  className?: string;
  children: React.ReactNode;
  target?: string;
  rel?: string;
}) {
  return (
    <a href={href} target={target} rel={rel} className={className} onClick={() => trackEvent(event, params)}>
      {children}
    </a>
  );
}
