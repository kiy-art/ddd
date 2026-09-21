"use client";

import { useEffect, useState } from "react";

import { useAdminAuth } from "@/lib/adminAuth";
import { PageStat, adminGetTopPages } from "@/lib/api";

export default function AdminAnalyticsPage() {
  const { token } = useAdminAuth();
  const [pages, setPages] = useState<PageStat[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    let ignore = false;
    adminGetTopPages(token)
      .then((data) => {
        if (!ignore) {
          setPages(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (!ignore) {
          setError(err instanceof Error ? err.message : String(err));
          setLoading(false);
        }
      });
    return () => {
      ignore = true;
    };
  }, [token]);

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="font-display text-xl font-semibold text-foreground">アクセス解析（過去28日）</h1>
        <p className="mt-1 text-sm text-foreground/50">
          Google アナリティクス（GA4）の実データです。ページビュー数が多い順に表示しています。
          「サイトを更新して」とチャットで依頼すると、ここに見えるデータをもとに改善を検討します。
        </p>
      </div>

      {loading && <p className="text-sm text-foreground/50">読み込み中...</p>}

      {error && (
        <div className="rounded-2xl border border-border bg-card p-5 text-sm text-red-600">
          <p className="font-semibold">取得に失敗しました</p>
          <p className="mt-1 text-foreground/60">{error}</p>
          <p className="mt-3 text-xs text-foreground/45">
            GA4_PROPERTY_ID / GA4_SERVICE_ACCOUNT_JSON がRenderのバックエンドに正しく設定・反映されているかご確認ください。
          </p>
        </div>
      )}

      {!loading && !error && pages.length === 0 && (
        <p className="rounded-2xl border border-dashed border-border bg-card px-4 py-16 text-center text-sm text-foreground/50">
          データがありません。まだアクセスが少ないか、計測期間が短い可能性があります。
        </p>
      )}

      {pages.length > 0 && (
        <div className="overflow-x-auto rounded-2xl border border-border bg-card">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-border text-xs text-foreground/50">
              <tr>
                <th className="p-3">ページ</th>
                <th className="p-3">表示回数</th>
                <th className="p-3">アクティブユーザー</th>
                <th className="p-3">直帰率</th>
                <th className="p-3">平均エンゲージメント時間</th>
              </tr>
            </thead>
            <tbody>
              {pages.map((p) => (
                <tr key={p.path} className="border-b border-border">
                  <td className="p-3 text-xs">{p.path}</td>
                  <td className="p-3 text-xs">{p.pageviews.toLocaleString("ja-JP")}</td>
                  <td className="p-3 text-xs">{p.active_users.toLocaleString("ja-JP")}</td>
                  <td className="p-3 text-xs">{(p.bounce_rate * 100).toFixed(1)}%</td>
                  <td className="p-3 text-xs">{p.avg_engagement_seconds.toFixed(0)}秒</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
