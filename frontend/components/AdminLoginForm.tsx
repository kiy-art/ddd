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
    <div className="mx-auto flex max-w-sm flex-col gap-4 rounded-xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-900">
      <h1 className="text-lg font-semibold">管理画面ログイン</h1>
      <p className="text-sm text-zinc-500">
        バックエンドの <code className="rounded bg-zinc-100 px-1 dark:bg-zinc-800">ADMIN_API_TOKEN</code>{" "}
        を入力してください。
      </p>
      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <input
          type="password"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="管理者トークン"
          className="rounded-lg border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-800"
          autoFocus
        />
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          type="submit"
          disabled={loading || !value}
          className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50 dark:bg-white dark:text-zinc-900"
        >
          {loading ? "確認中..." : "ログイン"}
        </button>
      </form>
    </div>
  );
}
