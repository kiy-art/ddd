"use client";

import { useState } from "react";

import { useAdminAuth } from "@/lib/adminAuth";

export default function AdminLoginForm() {
  const { login } = useAdminAuth();
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    const ok = await login(value.trim());
    setLoading(false);
    if (!ok) setError("トークンが正しくありません。");
  };

  return (
    <div className="mx-auto flex w-full max-w-sm flex-col gap-4 rounded-2xl border border-border bg-card p-8">
      <h1 className="font-display text-lg font-semibold text-foreground">管理画面ログイン</h1>
      <p className="text-sm text-foreground/50">
        バックエンドの <code className="rounded bg-background px-1.5 py-0.5">ADMIN_API_TOKEN</code>{" "}
        を入力してください。
      </p>
      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <input
          type="password"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="管理者トークン"
          className="rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground"
          autoFocus
        />
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          type="submit"
          disabled={loading || !value}
          className="rounded-full bg-brand px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
        >
          {loading ? "確認中..." : "ログイン"}
        </button>
      </form>
    </div>
  );
}
