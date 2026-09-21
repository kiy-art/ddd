// Minimal, privacy-conscious analytics hook. No-ops unless
// NEXT_PUBLIC_GA_ID is configured (see components loaded in app/layout.tsx),
// so nothing is collected, and no third-party script loads, until the site
// owner actually sets up GA4. No PII is ever attached to an event here.

declare global {
  interface Window {
    gtag?: (...args: unknown[]) => void;
  }
}

export const GA_MEASUREMENT_ID = process.env.NEXT_PUBLIC_GA_ID || "";

export function trackEvent(name: string, params?: Record<string, string | number | boolean>) {
  if (typeof window === "undefined" || !window.gtag) return;
  window.gtag("event", name, params);
}
