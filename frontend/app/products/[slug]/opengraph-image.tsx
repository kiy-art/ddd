import { ImageResponse } from "next/og";

import { getProduct } from "@/lib/api";

export const alt = "PAR. BUY SIGNAL";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

function yen(value: number | null): string {
  if (value === null) return "-";
  return `¥${value.toLocaleString("ja-JP")}`;
}

export default async function Image({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const product = await getProduct(slug).catch(() => null);

  const name = product?.name ?? "PAR.";
  const brand = product?.brand ?? "";
  const price = product ? yen(product.current_price) : "";
  const pct = product?.price_change_percent ?? null;
  const pctLabel = pct !== null ? `${pct > 0 ? "+" : ""}${pct}% vs 30日平均` : "";
  const score = product?.buy_signal_score ?? null;

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          background: "#14130F",
          padding: "80px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <svg width="40" height="40" viewBox="0 0 32 32" fill="none">
            <circle cx="16" cy="16" r="13.5" stroke="#FAF9F6" strokeWidth="2" opacity="0.35" />
            <path d="M16 2.5 A13.5 13.5 0 0 1 27.8 22" stroke="#FAF9F6" strokeWidth="2" strokeLinecap="round" />
            <circle cx="27.8" cy="22" r="2.4" fill="#C1521A" />
          </svg>
          <span style={{ fontSize: 32, fontWeight: 600, color: "#FAF9F6" }}>PAR. BUY SIGNAL</span>
        </div>

        <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            {brand && <span style={{ display: "flex", fontSize: 24, color: "#E2762F" }}>{brand}</span>}
            <span
              style={{
                display: "flex",
                fontSize: 48,
                fontWeight: 600,
                color: "#FAF9F6",
                lineHeight: 1.25,
                maxWidth: 760,
              }}
            >
              {name}
            </span>
            <span style={{ display: "flex", fontSize: 56, fontWeight: 700, color: "#FAF9F6" }}>{price}</span>
            {pctLabel && <span style={{ display: "flex", fontSize: 24, color: "#E2762F" }}>{pctLabel}</span>}
          </div>
          {score !== null && (
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                width: 200,
                height: 200,
                borderRadius: 100,
                border: "8px solid #C1521A",
              }}
            >
              <span style={{ display: "flex", fontSize: 64, fontWeight: 700, color: "#FAF9F6" }}>{score}</span>
              <span style={{ display: "flex", fontSize: 16, color: "#E2762F", letterSpacing: 2 }}>BUY SIGNAL</span>
            </div>
          )}
        </div>
      </div>
    ),
    { ...size }
  );
}
