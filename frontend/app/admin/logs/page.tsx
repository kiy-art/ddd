"use client";

import { useEffect, useState } from "react";

import { useAdminAuth } from "@/lib/adminAuth";
import { adminGetLogs, ErrorLog } from "@/lib/api";

export default function AdminLogsPage() {
  const { token } = useAdminAuth();
  const [logs, setLogs] = useState<ErrorLog[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    adminGetLogs(token).then((data) => {
      setLogs(data);
      setLoading(false);
    });
  }, [token]);

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-bold">エラーログ</h1>
      {loading && <p className="text-sm text-zinc-500">読み込み中...</p>}
      {!loading && logs.length === 0 && <p className="text-sm text-zinc-500">ログはありません。</p>}
      <div className="overflow-x-auto rounded-xl border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-zinc-200 text-xs text-zinc-500 dark:border-zinc-800">
            <tr>
              <th className="p-3">日時</th>
              <th className="p-3">種別</th>
              <th className="p-3">レベル</th>
              <th className="p-3">商品ID</th>
              <th className="p-3">メッセージ</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((log) => (
              <tr key={log.id} className="border-b border-zinc-100 dark:border-zinc-800">
                <td className="whitespace-nowrap p-3 text-xs text-zinc-500">
                  {new Date(log.created_at).toLocaleString("ja-JP")}
                </td>
                <td className="p-3 text-xs">{log.source}</td>
                <td className="p-3 text-xs">
                  <span
                    className={
                      log.level === "error" ? "font-semibold text-red-600" : "text-zinc-500"
                    }
                  >
                    {log.level}
                  </span>
                </td>
                <td className="p-3 text-xs">{log.product_id ?? "-"}</td>
                <td className="p-3 text-xs">{log.message}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
