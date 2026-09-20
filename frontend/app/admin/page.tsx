"use client";

import { useEffect, useState } from "react";

import { adminImportCsv, adminListProducts, adminRunUpdate, Product } from "@/lib/api";
import { useAdminAuth } from "@/lib/adminAuth";

export default function AdminDashboard() {
  const { token } = useAdminAuth();
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    if (!token) return;
    const data = await adminListProducts(token);
    setProducts(data);
    setLoading(false);
  };

  useEffect(() => {
    if (!token) return;
    let ignore = false;
    adminListProducts(token).then((data) => {
      if (!ignore) {
        setProducts(data);
        setLoading(false);
      }
    });
    return () => {
      ignore = true;
    };
  }, [token]);

  const handleCsv = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !token) return;
    setBusy(true);
    setMessage(null);
    try {
      const result = await adminImportCsv(token, file);
      setMessage(
        `インポート完了: 新規${result.created_products}件 / 更新${result.updated_products}件 / エラー${result.errors.length}件`
      );
      await load();
    } catch (err) {
      setMessage(`インポート失敗: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setBusy(false);
      e.target.value = "";
    }
  };

  const handleRunUpdate = async () => {
    if (!token) return;
    setBusy(true);
    setMessage(null);
    try {
      const result = await adminRunUpdate(token);
      setMessage(
        `分析パイプライン実行完了: 対象${result.products_checked}件 / AI再生成${result.ai_regenerated}件`
      );
      await load();
    } catch (err) {
      setMessage(`実行失敗: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setBusy(false);
    }
  };

  const byScore = products.reduce<Record<string, number>>((acc, p) => {
    acc[p.buy_score] = (acc[p.buy_score] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-bold">ダッシュボード</h1>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
        <StatCard label="商品数" value={products.length} />
        <StatCard label="強い買い時" value={byScore.strong_buy ?? 0} />
        <StatCard label="買い時" value={byScore.buy ?? 0} />
        <StatCard label="様子見" value={byScore.neutral ?? 0} />
        <StatCard label="判定不能" value={byScore.insufficient_data ?? 0} />
      </div>

      <div className="flex flex-col gap-3 rounded-xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
        <h2 className="font-semibold">価格CSVインポート</h2>
        <p className="text-sm text-zinc-500">
          product_name,brand,category,model_number,price,product_url,image_url の列を持つCSVを取り込みます。
        </p>
        <input type="file" accept=".csv" onChange={handleCsv} disabled={busy} className="text-sm" />
      </div>

      <div className="flex flex-col gap-3 rounded-xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
        <h2 className="font-semibold">分析・AI説明文の再生成</h2>
        <p className="text-sm text-zinc-500">
          全商品の買い時判定を再計算し、価格が変化した商品のみAI説明文を再生成します。
        </p>
        <button
          onClick={handleRunUpdate}
          disabled={busy}
          className="w-fit rounded-lg bg-zinc-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50 dark:bg-white dark:text-zinc-900"
        >
          今すぐ実行
        </button>
      </div>

      {message && <p className="text-sm text-zinc-700 dark:text-zinc-300">{message}</p>}
      {loading && <p className="text-sm text-zinc-500">読み込み中...</p>}
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
      <div className="text-xs text-zinc-500">{label}</div>
      <div className="text-2xl font-bold">{value}</div>
    </div>
  );
}
