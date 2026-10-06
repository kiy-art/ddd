"use client";

import Link from "next/link";
import { useState } from "react";

import { createPriceAlert } from "@/lib/api";
import { trackEvent } from "@/lib/analytics";

// A target price the visitor can pick with one tap - always a real number
// from this page (record low, forecast, or a plain "5% below today"), and
// labeled with where it comes from.
export type AlertSuggestion = { label: string; price: number };

function yen(value: number): string {
  return `¥${value.toLocaleString("ja-JP")}`;
}

// STEP69: "inline" sits right under the page's "様子見" verdict - the
// visitor who isn't buying today is offered a way to be told when the
// price drops instead of just leaving. "card" is the original standalone
// block further down the page.
export default function PriceAlertForm({
  slug,
  currentPrice,
  variant = "card",
  suggestions = [],
}: {
  slug: string;
  currentPrice: number | null;
  variant?: "card" | "inline";
  suggestions?: AlertSuggestion[];
}) {
  const [email, setEmail] = useState("");
  const [targetPrice, setTargetPrice] = useState(suggestions[0] ? String(suggestions[0].price) : "");
  const [status, setStatus] = useState<"idle" | "loading" | "done" | "error">("idle");
  // STEP75 (approval #003): unticked by default; the backend also refuses
  // a registration without it.
  const [consent, setConsent] = useState(false);
  const [consentError, setConsentError] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !targetPrice) return;
    if (!consent) {
      setConsentError(true);
      return;
    }
    setStatus("loading");
    try {
      await createPriceAlert(slug, email, Number(targetPrice), consent);
      trackEvent("price_alert_created", { product_slug: slug, target_price: Number(targetPrice), placement: variant });
      setStatus("done");
    } catch {
      setStatus("error");
    }
  };

  if (status === "done") {
    return (
      <div className="rounded-2xl border border-brand/30 bg-mint p-5 text-sm text-foreground/75">
        ✓ 設定しました。{yen(Number(targetPrice))}以下になったらメールでお知らせします。
      </div>
    );
  }

  const inline = variant === "inline";

  return (
    <div className={inline ? "rounded-2xl border border-brand/25 bg-mint p-5" : "rounded-2xl border border-border bg-card p-6"}>
      {inline ? (
        <>
          <p className="font-display text-base font-semibold text-foreground">🔔 値下がりしたらメールでお知らせ</p>
          <p className="mt-1 text-xs text-foreground/55">
            今すぐ買わない場合は、目標価格を決めておくと買い時を逃しません。登録はメールアドレスだけ・無料です。
          </p>
        </>
      ) : (
        <>
          <span className="text-xs font-medium uppercase tracking-widest text-foreground/40">Price Alert</span>
          <h3 className="mt-1 font-display text-lg font-semibold text-foreground">値下がり通知を設定</h3>
          <p className="mt-1 text-sm text-foreground/50">
            指定した価格以下になったらメールでお知らせします。
            {currentPrice !== null && `（現在価格 ${yen(currentPrice)}）`}
          </p>
        </>
      )}

      {suggestions.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {suggestions.map((s) => {
            const active = targetPrice === String(s.price);
            return (
              <button
                key={s.label}
                type="button"
                onClick={() => setTargetPrice(String(s.price))}
                aria-pressed={active}
                className={`tap rounded-full border px-3 py-1.5 text-xs font-semibold transition-colors ${
                  active ? "border-brand bg-brand text-on-brand" : "border-border bg-white text-foreground/70 hover:border-brand/40"
                }`}
              >
                {s.label} <span className="font-num">{yen(s.price)}</span>
              </button>
            );
          })}
        </div>
      )}

      <form onSubmit={handleSubmit} className="mt-3 flex flex-col gap-2.5">
        <div className="flex flex-col gap-2.5 sm:flex-row">
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
            min={1}
            placeholder="目標価格（円）"
            value={targetPrice}
            onChange={(e) => setTargetPrice(e.target.value)}
            className="w-full rounded-lg border border-border bg-background px-3 py-2.5 text-sm text-foreground sm:w-40"
          />
        </div>
        <label className="flex min-h-11 cursor-pointer items-center gap-2.5 text-xs text-foreground/75">
          <input
            type="checkbox"
            checked={consent}
            onChange={(e) => {
              setConsent(e.target.checked);
              if (e.target.checked) setConsentError(false);
            }}
            aria-invalid={consentError}
            aria-describedby={consentError ? `consent-error-${variant}` : undefined}
            className="h-5 w-5 shrink-0 accent-brand"
          />
          <span>
            <Link href="/privacy" target="_blank" rel="noopener" className="font-semibold text-brand underline">
              プライバシーポリシー
            </Link>
            （米国のResend社へのメールアドレスの提供を含む）に同意して登録する
          </span>
        </label>
        {consentError && (
          <p id={`consent-error-${variant}`} role="alert" className="text-xs text-red-600">
            登録するには、プライバシーポリシーへの同意のチェックが必要です。
          </p>
        )}
        <button
          type="submit"
          disabled={status === "loading"}
          className="tap w-full shrink-0 rounded-full sm:w-auto sm:self-start bg-brand px-5 py-2.5 text-sm font-semibold text-on-brand disabled:opacity-50"
        >
          {status === "loading" ? "設定中..." : "通知を受け取る"}
        </button>
      </form>
      {status === "error" && <p className="mt-2 text-xs text-red-600">設定に失敗しました。もう一度お試しください。</p>}
      <p className="mt-2 text-[11px] leading-relaxed text-foreground/65">
        メールアドレスは値下がり通知の送信と、その停止の受付にのみ使います。メールの送信には米国のResend社のサービスを使います（
        <a
          href="https://www.ppc.go.jp/enforcement/infoprovision/laws/offshore_report_america/"
          target="_blank"
          rel="noopener noreferrer"
          className="underline"
        >
          米国の個人情報保護の制度
        </a>
        ）。通知はメール内のリンクからいつでも停止できます。
      </p>
    </div>
  );
}
