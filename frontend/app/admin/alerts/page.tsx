"use client";

import { useEffect, useState } from "react";

import { useAdminAuth } from "@/lib/adminAuth";
import { PriceAlertAdmin, adminGetPriceAlerts } from "@/lib/api";

function yen(value: number | null): string {
  if (value === null) return "-";
  return `¥${value.toLocaleString("ja-JP")}`;
}

export default function AdminAlertsPage() {
  const { token } = useAdminAuth();
  const [alerts, setAlerts] = useState<PriceAlertAdmin[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    adminGetPriceAlerts(token).then((data) => {
      setAlerts(data);
      setLoading(false);
    });
  }, [token]);

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="font-display text-xl font-semibold text-foreground">価格アラート</h1>
        <p className="mt-1 text-sm text-foreground/50">
          「指定価格以下になったら知らせる」というユーザーからの登録一覧です。メール配信サービスが
          未設定のため、自動送信はまだ行われません。目標価格に到達（達成済み）した行を確認し、
          必要に応じて手動でご案内ください。
        </p>
      </div>
      {loading && <p className="text-sm text-foreground/50">読み込み中...</p>}
      {!loading && alerts.length === 0 && <p className="text-sm text-foreground/50">登録はありません。</p>}
      {alerts.length > 0 && (
        <div className="overflow-x-auto rounded-2xl border border-border bg-card">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-border text-xs text-foreground/50">
              <tr>
                <th className="p-3">登録日時</th>
                <th className="p-3">商品</th>
                <th className="p-3">メール</th>
                <th className="p-3">目標価格</th>
                <th className="p-3">現在価格</th>
                <th className="p-3">状態</th>
              </tr>
            </thead>
            <tbody>
              {alerts.map((a) => (
                <tr key={a.id} className="border-b border-border">
                  <td className="whitespace-nowrap p-3 text-xs text-foreground/50">
                    {new Date(a.created_at).toLocaleString("ja-JP")}
                  </td>
                  <td className="p-3 text-xs">{a.product_name}</td>
                  <td className="p-3 text-xs">{a.email}</td>
                  <td className="p-3 text-xs">{yen(a.target_price)}</td>
                  <td className="p-3 text-xs">{yen(a.current_price)}</td>
                  <td className="p-3 text-xs">
                    {a.triggered ? (
                      <span className="font-semibold text-brand dark:text-brand-light">達成済み</span>
                    ) : (
                      <span className="text-foreground/45">未達</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
