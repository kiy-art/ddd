"use client";

import { useState } from "react";

import { createPriceAlert } from "@/lib/api";
import { trackEvent } from "@/lib/analytics";

export default function PriceAlertForm({ slug, currentPrice }: { slug: string; currentPrice: number | null }) {
  const [email, setEmail] = useState("");
  const [targetPrice, setTargetPrice] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "done" | "error">("idle");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !targetPrice) return;
    setStatus("loading");
    try {
      await createPriceAlert(slug, email, Number(targetPrice));
      trackEvent("price_alert_created", { product_slug: slug, target_price: Number(targetPrice) });
      setStatus("done");
    } catch {
      setStatus("error");
    }
  };

  if (status === "done") {
    return (
      <div className="rounded-2xl border border-border bg-card p-6 text-sm text-foreground/70">
        ✓ 設定しました。指定価格以下になった際にメールでお知らせします。
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-border bg-card p-6">
      <span className="text-xs font-medium uppercase tracking-widest text-foreground/40">Price Alert</span>
      <h3 className="mt-1 font-display text-lg font-semibold text-foreground">値下がり通知を設定</h3>
      <p className="mt-1 text-sm text-foreground/50">
        指定した価格以下になったらメールでお知らせします。
        {currentPrice !== null && `（現在価格 ¥${currentPrice.toLocaleString("ja-JP")}）`}
      </p>
      <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-3 sm:flex-row">
        <input
          type="email"
          required
          placeholder="メールアドレス"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="flex-1 rounded-lg border border-border bg-background px-3 py-2.5 text-sm text-foreground"
        />
        <input
          type="number"
          required
          placeholder="目標価格（円）"
          value={targetPrice}
          onChange={(e) => setTargetPrice(e.target.value)}
          className="w-full rounded-lg border border-border bg-background px-3 py-2.5 text-sm text-foreground sm:w-40"
        />
        <button
          type="submit"
          disabled={status === "loading"}
          className="shrink-0 rounded-full bg-brand px-5 py-2.5 text-sm font-semibold text-on-brand disabled:opacity-50"
        >
          {status === "loading" ? "設定中..." : "通知を設定"}
        </button>
      </form>
      {status === "error" && <p className="mt-2 text-xs text-red-600">設定に失敗しました。もう一度お試しください。</p>}
    </div>
  );
}
