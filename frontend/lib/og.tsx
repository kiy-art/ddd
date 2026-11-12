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

// STEP60 "Clean Fairway": a light share card to match the site (was
// STEP50's dark panel). Names kept for the existing call sites: `ink` is
// the card BACKGROUND, `paper` the main TEXT color, `accentLight` the
// emerald used for accent text.
export const OG_COLORS = {
  ink: "#ECFDF5",
  paper: "#14201B",
  accent: "#047857",
  accentLight: "#047857",
  muted: "#5B6B64",
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

// 2026-11-08 (社長指示: X投稿のカード画像を「つい押したくなる」形に):
// a real, recent price STEP - the price sat at one level for several
// recorded days, then dropped. Only steps are used (not a listing swap
// that bounces up and down): every record in the stable window before
// the drop must be the same price, and nothing after it may be higher
// than the new price. Returns null when there is no such drop in the
// last 14 days or it is under 5% - the card then keeps its old layout.
export interface RecentDrop {
  before: number;
  after: number;
  yenDown: number;
  percentDown: number;
  stableDays: number;
  dropDate: string; // YYYY-MM-DD (JST)
  daysAgo: number;
}

const DAY_MS = 86_400_000;
const jstDate = (iso: string) => new Date(new Date(iso).getTime() + 9 * 3_600_000).toISOString().slice(0, 10);

export function findRecentDrop(product: ProductDetail, now: number = Date.now()): RecentDrop | null {
  const current = product.current_price;
  const history = (product.price_history || [])
    .filter((h) => typeof h.price === "number" && h.price > 0 && h.recorded_at)
    .slice()
    .sort((a, b) => new Date(a.recorded_at).getTime() - new Date(b.recorded_at).getTime());
  if (current === null || history.length < 6) return null;

  // Walk back from the newest record to the first one that isn't the current price.
  let i = history.length - 1;
  while (i >= 0 && history[i].price <= current) i--;
  if (i < 0) return null;
  const dropRecord = history[i + 1];
  if (!dropRecord || now - new Date(dropRecord.recorded_at).getTime() > 14 * DAY_MS) return null;

  // The stable level right before the drop.
  const before = history[i].price;
  let j = i;
  while (j >= 0 && history[j].price === before) j--;
  const stableStart = history[j + 1];
  const stableDays = Math.round(
    (new Date(history[i].recorded_at).getTime() - new Date(stableStart.recorded_at).getTime()) / DAY_MS
  );
  if (i - j < 3 || stableDays < 3) return null;

  const yenDown = before - current;
  const percentDown = Math.round((yenDown / before) * 100);
  if (yenDown <= 0 || yenDown / before < 0.05) return null;

  return {
    before,
    after: current,
    yenDown,
    percentDown,
    stableDays,
    dropDate: jstDate(dropRecord.recorded_at),
    daysAgo: Math.max(0, Math.floor((now - new Date(dropRecord.recorded_at).getTime()) / DAY_MS)),
  };
}

// "今日" / "昨日" / "3日前" / "2週間以内" - when the drop was recorded.
export function dropWhen(drop: RecentDrop): string {
  return drop.daysAgo === 0 ? "今日" : drop.daysAgo === 1 ? "昨日" : drop.daysAgo <= 6 ? `${drop.daysAgo}日前` : "2週間以内";
}

// 2026-11-12 (社長指示: Xのカード画像を「一目で押したくなる」ものに):
// "値下がり速報" look - near-black card, one huge yellow number, a red
// percent badge on the product photo and a button-shaped call to action.
// The old cards were light green with every line in the same regular
// weight (no bold font was loaded, so fontWeight 700 rendered as regular).
export const POP = {
  bg: "#0B100D",
  panel: "#18211C",
  yellow: "#FFE600",
  red: "#FF3B30",
  white: "#FFFFFF",
  gray: "#A7B3AD",
  black: "#0B100D",
};

type OgFont = { name: string; data: ArrayBuffer; weight: 500 | 900; style: "normal" };

async function fetchGoogleFont(weight: 500 | 900, text: string): Promise<ArrayBuffer | null> {
  try {
    // An old Safari UA makes Google Fonts answer with a TrueType subset
    // (satori can't read woff2). `text=` keeps it to the glyphs on the card.
    const css = await fetch(
      `https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@${weight}&text=${encodeURIComponent(text)}`,
      {
        signal: AbortSignal.timeout(2500),
        headers: {
          "User-Agent":
            "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_8; de-at) AppleWebKit/533.21.1 (KHTML, like Gecko) Version/5.0.5 Safari/533.21.1",
        },
        cache: "no-store",
      }
    ).then((r) => r.text());
    const match = css.match(/src: url\((.+?)\) format\('(?:opentype|truetype)'\)/);
    if (!match) return null;
    const res = await fetch(match[1], { signal: AbortSignal.timeout(2500), cache: "no-store" });
    return res.ok ? await res.arrayBuffer() : null;
  } catch {
    return null;
  }
}

// Heavy (900) + medium (500) Noto Sans JP for exactly the characters on a
// card. Rule 1 above still holds: if Google Fonts is slow or down this
// returns undefined and the card renders in next/og's default font.
export async function ogFonts(texts: Array<string | null | undefined>): Promise<OgFont[] | undefined> {
  const text = Array.from(new Set(`${texts.filter(Boolean).join("")}0123456789¥,.%-+→・…！？／() PARpar-gear.com`)).join("");
  const [black, medium] = await Promise.all([fetchGoogleFont(900, text), fetchGoogleFont(500, text)]);
  const fonts: OgFont[] = [];
  if (black) fonts.push({ name: "PAR", data: black, weight: 900, style: "normal" });
  if (medium) fonts.push({ name: "PAR", data: medium, weight: 500, style: "normal" });
  return fonts.length ? fonts : undefined;
}

export function BrandMark({ label = "PAR.", size = 40 }: { label?: string; size?: number }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
      <svg width={size} height={size} viewBox="0 0 32 32" fill="none">
        <circle cx="16" cy="16" r="13.5" stroke={POP.white} strokeWidth="2.5" opacity="0.35" />
        <path d="M16 2.5 A13.5 13.5 0 0 1 27.8 22" stroke={POP.white} strokeWidth="2.5" strokeLinecap="round" />
        <circle cx="27.8" cy="22" r="2.6" fill={POP.yellow} />
      </svg>
      <span style={{ display: "flex", fontSize: size * 0.8, fontWeight: 900, color: POP.white }}>{label}</span>
    </div>
  );
}

// Yellow label, top-left of a card ("値下がり速報", a hook, a category).
export function HookChip({ text }: { text: string }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        background: POP.yellow,
        color: POP.black,
        fontSize: 30,
        fontWeight: 900,
        padding: "6px 22px 8px",
        borderRadius: 10,
      }}
    >
      {text}
    </div>
  );
}

// Button-shaped call to action - the thing that says "this card opens something".
export function CtaPill({ text }: { text: string }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 14,
        background: POP.white,
        color: POP.black,
        fontSize: 30,
        fontWeight: 900,
        padding: "12px 30px 14px",
        borderRadius: 999,
      }}
    >
      <span style={{ display: "flex" }}>{text}</span>
      <svg width="22" height="24" viewBox="0 0 22 24">
        <path d="M2 2 L20 12 L2 22 Z" fill={POP.red} />
      </svg>
    </div>
  );
}

// Red round "-25%" sticker, tilted, meant to overlap a photo's corner.
export function PercentBadge({ text, size = 150, caption }: { text: string; size?: number; caption?: string }) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        width: size,
        height: size,
        borderRadius: size,
        background: POP.red,
        border: `${Math.round(size / 25)}px solid ${POP.white}`,
        transform: "rotate(-10deg)",
      }}
    >
      {caption && (
        <span style={{ display: "flex", fontSize: size * 0.13, fontWeight: 900, color: POP.white, marginBottom: -4 }}>
          {caption}
        </span>
      )}
      <span style={{ display: "flex", fontSize: size * (text.length > 4 ? 0.25 : 0.3), fontWeight: 900, color: POP.white }}>
        {text}
      </span>
    </div>
  );
}

export function PhotoTile({ src, size, badge, badgeCaption }: { src: string; size: number; badge?: string | null; badgeCaption?: string }) {
  const badgeSize = Math.round(size * 0.42);
  return (
    <div style={{ display: "flex", position: "relative", width: size, height: size }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          width: size,
          height: size,
          background: "#FFFFFF",
          borderRadius: Math.round(size * 0.1),
          overflow: "hidden",
        }}
      >
        {/* eslint-disable-next-line @next/next/no-img-element -- satori renders plain <img>, next/image isn't available here */}
        <img src={src} width={size - 36} height={size - 36} style={{ objectFit: "contain" }} alt="" />
      </div>
      {badge && (
        <div style={{ display: "flex", position: "absolute", top: -Math.round(badgeSize * 0.3), left: -Math.round(badgeSize * 0.35) }}>
          <PercentBadge text={badge} size={badgeSize} caption={badgeCaption} />
        </div>
      )}
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
        fontWeight: 500,
        color: POP.gray,
      }}
    >
      <span style={{ display: "flex" }}>par-gear.com</span>
      <span style={{ display: "flex" }}>{right}</span>
    </div>
  );
}

// A category/guide/home share card: big headline (last line in yellow), a
// button-shaped call to action and up to two real product photos, each
// with an optional red percent badge. Photos that can't be fetched are
// simply left out; with none at all the card is text-only - still a real
// card, never a grey placeholder.
export function CollectionCard({
  eyebrow,
  title,
  subtitle,
  photos,
  footerRight,
  badges,
  badgeCaption,
  cta = "いまの値段を見る",
}: {
  eyebrow: string;
  title: string;
  subtitle: string | null;
  photos: string[];
  footerRight: string;
  badges?: Array<string | null>;
  badgeCaption?: string;
  cta?: string;
}) {
  const lines = title.split("\n");
  const longest = Math.max(...lines.map((l) => l.length));
  const shown = photos.slice(0, photos.length === 1 ? 1 : 2);
  // Text column is ~600px with photos, ~1080px without.
  // Long single-line titles (guides) wrap at a readable size instead of shrinking.
  const titleSize = Math.max(shown.length ? 52 : 60, Math.min(shown.length ? 84 : 96, Math.floor((shown.length ? 540 : 1080) / longest)));
  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        background: POP.bg,
        padding: "44px 56px 36px",
        fontFamily: "PAR",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <BrandMark size={36} />
        <HookChip text={eyebrow} />
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 44 }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 18, flex: 1 }}>
          {/* One block per "\n" line: satori ignores newlines inside a text node. */}
          <div style={{ display: "flex", flexDirection: "column" }}>
            {lines.map((line, i) => (
              <span
                key={i}
                style={{
                  display: "flex",
                  fontSize: titleSize,
                  fontWeight: 900,
                  color: lines.length > 1 && i === lines.length - 1 ? POP.yellow : POP.white,
                  lineHeight: 1.2,
                }}
              >
                {line}
              </span>
            ))}
          </div>
          {subtitle && (
            <span style={{ display: "flex", fontSize: 25, fontWeight: 500, color: POP.white, lineHeight: 1.4 }}>{subtitle}</span>
          )}
          <div style={{ display: "flex", marginTop: 6 }}>
            <CtaPill text={cta} />
          </div>
        </div>
        {shown.length > 0 && (
          <div style={{ display: "flex", gap: 22, paddingTop: 30 }}>
            {shown.map((src, i) => (
              <PhotoTile key={i} src={src} size={shown.length === 1 ? 360 : 248} badge={badges?.[i]} badgeCaption={badgeCaption} />
            ))}
          </div>
        )}
      </div>
      <Footer right={footerRight} />
    </div>
  );
}
