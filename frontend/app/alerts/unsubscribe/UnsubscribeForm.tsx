"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { getUnsubscribeInfo, unsubscribePriceAlert, type PriceAlertUnsubscribeInfo } from "@/lib/api";

type State =
  | { kind: "loading" }
  | { kind: "missing" }
  | { kind: "ready"; info: PriceAlertUnsubscribeInfo }
  | { kind: "sending"; info: PriceAlertUnsubscribeInfo }
  | { kind: "done"; deleted: number }
  | { kind: "error"; info: PriceAlertUnsubscribeInfo };

const contactNote = (
  <p className="mt-4 text-xs text-foreground/65">
    うまくいかない場合は、
    <Link href="/contact" className="text-brand underline">
      お問い合わせフォーム
    </Link>
    から停止・削除をご依頼ください。
  </p>
);

export default function UnsubscribeForm({ token }: { token: string }) {
  const [state, setState] = useState<State>(token ? { kind: "loading" } : { kind: "missing" });
  const [allForEmail, setAllForEmail] = useState(false);

  useEffect(() => {
    if (!token) return;
    getUnsubscribeInfo(token)
      .then((info) => setState({ kind: "ready", info }))
      .catch(() => setState({ kind: "missing" }));
  }, [token]);

  if (state.kind === "loading") return <p className="text-sm text-foreground/65">確認しています…</p>;

  if (state.kind === "missing") {
    return (
      <div className="rounded-2xl border border-border bg-card p-6 text-sm text-foreground/75">
        <p>この通知は見つかりませんでした。すでに停止・削除済みの可能性があります。</p>
        {contactNote}
      </div>
    );
  }

  if (state.kind === "done") {
    return (
      <div className="rounded-2xl border border-brand/30 bg-mint p-6 text-sm text-foreground/75">
        <p>✓ 通知を停止し、登録の情報（{state.deleted}件）を削除しました。今後、この通知のメールは届きません。</p>
        <p className="mt-3">
          <Link href="/" className="text-brand underline">
            トップページへ
          </Link>
        </p>
      </div>
    );
  }

  const { info } = state;
  const submit = async () => {
    setState({ kind: "sending", info });
    try {
      const result = await unsubscribePriceAlert(token, allForEmail);
      setState({ kind: "done", deleted: result.deleted });
    } catch {
      setState({ kind: "error", info });
    }
  };

  return (
    <div className="rounded-2xl border border-border bg-card p-6 text-sm text-foreground/75">
      <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1">
        <dt className="text-foreground/65">商品</dt>
        <dd className="text-foreground">{info.product_name}</dd>
        <dt className="text-foreground/65">目標価格</dt>
        <dd className="font-num text-foreground">¥{info.target_price.toLocaleString("ja-JP")}</dd>
        <dt className="text-foreground/65">メールアドレス</dt>
        <dd className="text-foreground">{info.masked_email}</dd>
      </dl>
      {info.alerts_for_email > 1 && (
        <label className="mt-4 flex min-h-11 cursor-pointer items-center gap-2.5">
          <input
            type="checkbox"
            checked={allForEmail}
            onChange={(e) => setAllForEmail(e.target.checked)}
            className="h-5 w-5 shrink-0 accent-brand"
          />
          <span>このメールアドレスの登録をすべて削除する（{info.alerts_for_email}件）</span>
        </label>
      )}
      <p className="mt-4 text-xs text-foreground/65">停止すると、登録の情報は削除され、元に戻せません。</p>
      <button
        type="button"
        onClick={submit}
        disabled={state.kind === "sending"}
        className="tap mt-4 rounded-full bg-brand px-6 py-3 text-sm font-semibold text-on-brand disabled:opacity-50"
      >
        {state.kind === "sending" ? "停止しています…" : "通知を停止して削除する"}
      </button>
      {state.kind === "error" && <p className="mt-3 text-xs text-red-600">停止できませんでした。もう一度お試しください。</p>}
      {contactNote}
    </div>
  );
}
