// Shared building blocks for the generated share images
// (app/**/opengraph-image.tsx) - the card X/LINE/Facebook show when a
// par-gear.com link is posted.
//
// Two rules every image here follows:
// 1. Never fail. A share image that errors or times out is what makes X
//    fall back to a grey placeholder card - so every network call below
//    has a short timeout and a branded fallback, and a missing/unsupported
//    product photo just means the card is laid out without it.
// 2. Only real, already-computed facts - the same numbers the product page
//    itself shows (see marketing_playbook.py's 景品表示法 rules on the
//    backend: a "最安値" claim only with enough real price history, a
//    discount only against the recorded MSRP).

import type { ProductDetail } from "@/lib/api";
import { normalizeImageUrl } from "@/lib/imageUrl";

export const OG_SIZE = { width: 1200, height: 630 };

export const OG_COLORS = {
  ink: "#14130F",
  paper: "#FAF9F6",
  accent: "#C1521A",
  accentLight: "#E2762F",
  muted: "#A8A69E",
};

// Render's free plan sleeps the backend after inactivity; its cold start
// can take far longer than a link-preview crawler waits. Better a branded
// card without live numbers than no card at all.
export const OG_API_TIMEOUT_MS = 5000;
const OG_IMAGE_TIMEOUT_MS = 3000;
const OG_IMAGE_MAX_BYTES = 2_000_000;

// Satori (next/og's renderer) decodes PNG/JPEG reliably; anything else
// (WebP, AVIF, SVG from a shop CDN) is skipped rather than risking a
// render error that would take the whole card down.
const SUPPORTED_IMAGE_TYPES = new Set(["image/jpeg", "image/png"]);

// Same threshold used across the site for "enough price history to claim
// a trend" (AiBuySignal.tsx, ProductCard.tsx, the product page).
export const THIN_DATA_DAYS = 7;

export function yen(value: number | null | undefined): string {
  if (value === null || value === undefined) return "-";
  return `¥${value.toLocaleString("ja-JP")}`;
}

export function truncate(text: string, max: number): string {
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}

function sizedImageUrl(url: string): string {
  // Rakuten's thumbnail CDN serves the original upload (sometimes several
  // MB) unless asked for a size; 600px is plenty for a 400px card slot.
  try {
    const parsed = new URL(url);
    if (parsed.hostname === "thumbnail.image.rakuten.co.jp" && !parsed.searchParams.has("_ex")) {
      parsed.searchParams.set("_ex", "600x600");
      return parsed.toString();
    }
  } catch {
    // not a valid absolute URL - fetch() below will fail and return null
  }
  return url;
}

export async function fetchImageDataUri(raw: string | null | undefined): Promise<string | null> {
  // Same normalization as every on-page photo (http -> https, junk -> null);
  // a same-site relative path can't be fetched from this server-side
  // renderer, so it's treated as "no photo" here.
  const url = normalizeImageUrl(raw);
  if (!url || url.startsWith("/")) return null;
  try {
    const res = await fetch(sizedImageUrl(url), {
      signal: AbortSignal.timeout(OG_IMAGE_TIMEOUT_MS),
      cache: "no-store",
    });
    if (!res.ok) return null;
    const type = (res.headers.get("content-type") || "").split(";")[0].trim().toLowerCase();
    if (!SUPPORTED_IMAGE_TYPES.has(type)) return null;
    const buffer = await res.arrayBuffer();
    if (buffer.byteLength === 0 || buffer.byteLength > OG_IMAGE_MAX_BYTES) return null;
    return `data:${type};base64,${Buffer.from(buffer).toString("base64")}`;
  } catch {
    return null;
  }
}

export async function withTimeout<T>(promise: Promise<T>, ms: number = OG_API_TIMEOUT_MS): Promise<T | null> {
  let timer: ReturnType<typeof setTimeout> | undefined;
  const timeout = new Promise<null>((resolve) => {
    timer = setTimeout(() => resolve(null), ms);
  });
  try {
    return await Promise.race([promise.catch(() => null), timeout]);
  } finally {
    if (timer) clearTimeout(timer);
  }
}

export interface ProductShareFacts {
  hasReliableTrend: boolean;
  savingsYen: number | null;
  savingsPercent: number | null;
  atRecordedLowest: boolean;
  // The single most eye-catching TRUE statement about this price, used as
  // the card's headline chip - or null when nothing notable is true.
  hook: string | null;
}

export function productShareFacts(product: ProductDetail): ProductShareFacts {
  const current = product.current_price;
  const hasReliableTrend =
    product.buy_score !== "insufficient_data" && product.history_span_days >= THIN_DATA_DAYS;

  const savingsYen =
    current !== null && product.msrp && product.msrp > current ? product.msrp - current : null;
  const savingsPercent =
    savingsYen !== null && product.msrp ? Math.round((savingsYen / product.msrp) * 100) : null;

  // "最安値" only with >= 7 days of real history - the same bar
  // content_rewriter._is_at_recorded_lowest applies on the backend.
  const atRecordedLowest =
    hasReliableTrend && current !== null && product.lowest_price !== null && current <= product.lowest_price;

  // Thresholds on the exact ratio, never the rounded percent: 49.7% off
  // displays as "-50%" but is not "半額以下" (有利誤認 risk). Same ladder as
  // the X post hook (backend app/x_post.py _hook).
  const ratio = savingsYen !== null && product.msrp ? savingsYen / product.msrp : null;

  let hook: string | null = null;
  if (atRecordedLowest) {
    hook = `過去${product.history_span_days}日間の最安値`;
  } else if (ratio !== null && ratio >= 0.5) {
    hook = "定価の半額以下";
  } else if (ratio !== null && ratio >= 0.45) {
    hook = "定価のほぼ半額";
  } else if (ratio !== null && ratio >= 0.3) {
    hook = `定価から${savingsPercent}%オフ`;
  } else if (hasReliableTrend && product.price_change_percent !== null && product.price_change_percent <= -5) {
    hook = `30日平均より${Math.abs(product.price_change_percent)}%安い`;
  }

  return { hasReliableTrend, savingsYen, savingsPercent, atRecordedLowest, hook };
}

export function BrandMark({ label = "PAR.", size = 40 }: { label?: string; size?: number }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
      <svg width={size} height={size} viewBox="0 0 32 32" fill="none">
        <circle cx="16" cy="16" r="13.5" stroke={OG_COLORS.paper} strokeWidth="2" opacity="0.35" />
        <path d="M16 2.5 A13.5 13.5 0 0 1 27.8 22" stroke={OG_COLORS.paper} strokeWidth="2" strokeLinecap="round" />
        <circle cx="27.8" cy="22" r="2.4" fill={OG_COLORS.accent} />
      </svg>
      <span style={{ display: "flex", fontSize: size * 0.8, fontWeight: 600, color: OG_COLORS.paper }}>{label}</span>
    </div>
  );
}

export function HookChip({ text }: { text: string }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        background: OG_COLORS.accent,
        color: OG_COLORS.paper,
        fontSize: 30,
        fontWeight: 700,
        padding: "10px 26px",
        borderRadius: 999,
      }}
    >
      {text}
    </div>
  );
}

export function PhotoTile({ src, size }: { src: string; size: number }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        width: size,
        height: size,
        background: "#FFFFFF",
        borderRadius: 32,
        overflow: "hidden",
      }}
    >
      {/* eslint-disable-next-line @next/next/no-img-element -- satori renders plain <img>, next/image isn't available here */}
      <img src={src} width={size - 48} height={size - 48} style={{ objectFit: "contain" }} alt="" />
    </div>
  );
}

export function Footer({ right }: { right: string }) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        fontSize: 22,
        color: OG_COLORS.muted,
      }}
    >
      <span style={{ display: "flex" }}>par-gear.com</span>
      <span style={{ display: "flex" }}>{right}</span>
    </div>
  );
}

// A category/guide share card: headline + up to three real product photos.
// Photos that can't be fetched are simply left out; with none at all the
// card is text-only - still a real card, never a grey placeholder.
export function CollectionCard({
  eyebrow,
  title,
  subtitle,
  photos,
  footerRight,
}: {
  eyebrow: string;
  title: string;
  subtitle: string | null;
  photos: string[];
  footerRight: string;
}) {
  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        background: OG_COLORS.ink,
        padding: "56px 64px",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <BrandMark size={36} />
        <span style={{ display: "flex", fontSize: 24, color: OG_COLORS.accentLight, letterSpacing: 2 }}>{eyebrow}</span>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 40 }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 16, flex: 1 }}>
          <span style={{ display: "flex", fontSize: photos.length ? 56 : 68, fontWeight: 700, color: OG_COLORS.paper, lineHeight: 1.25 }}>
            {title}
          </span>
          {subtitle && (
            <span style={{ display: "flex", fontSize: 28, color: OG_COLORS.accentLight, lineHeight: 1.4 }}>{subtitle}</span>
          )}
        </div>
        {photos.length > 0 && (
          <div style={{ display: "flex", gap: 16 }}>
            {photos.slice(0, photos.length === 1 ? 1 : 2).map((src, i) => (
              <PhotoTile key={i} src={src} size={photos.length === 1 ? 340 : 250} />
            ))}
          </div>
        )}
      </div>
      <Footer right={footerRight} />
    </div>
  );
}
