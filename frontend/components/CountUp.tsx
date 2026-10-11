"use client";

import { useEffect, useRef, useState } from "react";

// The first render - the server-rendered HTML included - shows the real value,
// so crawlers, no-JS readers, search snippets and AI extractors read "419" or
// "-12.3%", never the old initial "0". After mount, a change of `value` tweens
// from the number currently shown to the new one; with
// prefers-reduced-motion it jumps straight there.
export default function CountUp({
  value,
  duration = 900,
  decimals = 0,
  suffix = "",
  prefix = "",
}: {
  value: number;
  duration?: number;
  decimals?: number;
  suffix?: string;
  prefix?: string;
}) {
  const [display, setDisplay] = useState(value);
  const shownRef = useRef(value);

  useEffect(() => {
    const from = shownRef.current;
    if (from === value) return;

    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      const frame = requestAnimationFrame(() => {
        shownRef.current = value;
        setDisplay(value);
      });
      return () => cancelAnimationFrame(frame);
    }

    const start = performance.now();
    let frame: number;

    const tick = (now: number) => {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      const next = progress < 1 ? from + (value - from) * eased : value;
      shownRef.current = next;
      setDisplay(next);
      if (progress < 1) {
        frame = requestAnimationFrame(tick);
      }
    };

    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [value, duration]);

  return (
    <>
      {prefix}
      {display.toFixed(decimals)}
      {suffix}
    </>
  );
}
