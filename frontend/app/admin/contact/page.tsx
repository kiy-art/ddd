"use client";

import { useEffect, useState } from "react";

import { useAdminAuth } from "@/lib/adminAuth";
import { ContactMessage, adminGetContactMessages, adminMarkContactMessageRead } from "@/lib/api";

export default function AdminContactPage() {
  const { token } = useAdminAuth();
  const [messages, setMessages] = useState<ContactMessage[]>([]);
  const [loading, setLoading] = useState(true);

  const load = () => {
    if (!token) return;
    adminGetContactMessages(token).then((data) => {
      setMessages(data);
      setLoading(false);
    });
  };

  useEffect(load, [token]);

  const handleMarkRead = async (id: number) => {
    if (!token) return;
    await adminMarkContactMessageRead(token, id);
    load();
  };

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="font-display text-xl font-semibold text-foreground">お問い合わせ</h1>
        <p className="mt-1 text-sm text-foreground/50">
          お問い合わせフォームから送信されたメッセージの一覧です。メール配信サービスは未設定のため、
          返信が必要な場合は記載のメールアドレスへ直接ご連絡ください。
        </p>
      </div>
      {loading && <p className="text-sm text-foreground/50">読み込み中...</p>}
      {!loading && messages.length === 0 && <p className="text-sm text-foreground/50">お問い合わせはありません。</p>}
      <div className="flex flex-col gap-3">
        {messages.map((m) => (
          <div
            key={m.id}
            className={`rounded-2xl border p-5 ${
              m.read_at ? "border-border bg-card" : "border-brand/40 bg-card"
            }`}
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="text-sm font-semibold text-foreground">
                  {m.name || "（名前未入力）"} ・ {m.email}
                </div>
                <div className="text-xs text-foreground/45">
                  {new Date(m.created_at).toLocaleString("ja-JP")}
                </div>
              </div>
              {!m.read_at ? (
                <button
                  onClick={() => handleMarkRead(m.id)}
                  className="rounded-full border border-border px-3.5 py-1.5 text-xs font-semibold text-foreground/70 hover:border-foreground/30 hover:text-foreground"
                >
                  既読にする
                </button>
              ) : (
                <span className="text-xs text-foreground/35">既読</span>
              )}
            </div>
            <p className="mt-3 whitespace-pre-wrap text-sm text-foreground/70">{m.message}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
