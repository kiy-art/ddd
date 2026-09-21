"use client";

import { useEffect, useState } from "react";

import { useAdminAuth } from "@/lib/adminAuth";
import { adminFixPriceAnomalies, adminGetPriceAnomalies, PriceAnomaly } from "@/lib/api";

export default function AdminAnomaliesPage() {
  const { token } = useAdminAuth();
  const [anomalies, setAnomalies] = useState<PriceAnomaly[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    let ignore = false;
    adminGetPriceAnomalies(token).then((data) => {
      if (!ignore) {
        setAnomalies(data);
        setLoading(false);
      }
    });
    return () => {
      ignore = true;
    };
  }, [token]);

  const handleFix = async () => {
    if (!token) return;
    if (!confirm(`${anomalies.length}件の異常な価格データを削除して、各商品の価格・買い時判定を再計算します。よろしいですか？`))
      return;
    setBusy(true);
    setMessage(null);
    try {
      const fixed = await adminFixPriceAnomalies(token);
      setMessage(`修正完了: ${fixed.length}件の異常データを削除し、対象商品を再計算しました。`);
      setAnomalies([]);
    } catch (err) {
      setMessage(`修正失敗: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="font-display text-xl font-semibold text-foreground">価格異常チェック</h1>
        <p className="mt-1 text-sm text-foreground/50">
          各商品の価格履歴の中で、他の記録価格と比べて極端に安い・高い（目安として半額未満 or
          2倍超）データを自動検出します。楽天検索が誤った商品にマッチした場合に起きる異常です。
        </p>
      </div>

      {loading && <p className="text-sm text-foreground/50">確認中...</p>}

      {!loading && anomalies.length === 0 && !message && (
        <p className="rounded-2xl border border-border bg-card p-5 text-sm text-foreground/60">
          異常な価格データは見つかりませんでした。
        </p>
      )}

      {!loading && anomalies.length > 0 && (
        <>
          <button
            onClick={handleFix}
            disabled={busy}
            className="w-fit rounded-full bg-brand px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
          >
            検出された{anomalies.length}件を一括修正
          </button>

          <div className="overflow-x-auto rounded-2xl border border-border bg-card">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-border text-xs text-foreground/50">
                <tr>
                  <th className="p-3">商品名</th>
                  <th className="p-3">記録日時</th>
                  <th className="p-3">異常な価格</th>
                  <th className="p-3">他の記録価格の中央値</th>
                  <th className="p-3">倍率</th>
                </tr>
              </thead>
              <tbody>
                {anomalies.map((a) => (
                  <tr key={a.price_history_id} className="border-b border-border">
                    <td className="p-3">{a.product_name}</td>
                    <td className="whitespace-nowrap p-3 text-xs text-foreground/50">
                      {new Date(a.recorded_at).toLocaleString("ja-JP")}
                    </td>
                    <td className="p-3 font-semibold text-red-600">¥{a.price.toLocaleString("ja-JP")}</td>
                    <td className="p-3">¥{a.reference_price.toLocaleString("ja-JP")}</td>
                    <td className="p-3">{a.ratio}倍</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {message && <p className="text-sm text-foreground/70">{message}</p>}
    </div>
  );
}
