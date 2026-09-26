"use client";

import { useEffect, useState } from "react";

import {
  AiOptimizationAction,
  ImprovementOpportunity,
  adminDiscoverProducts,
  adminBackfillImages,
  adminFetchRakuten,
  adminGetImprovementOpportunities,
  adminGetXPostPreview,
  adminImportCsv,
  adminListOptimizationActions,
  adminListProducts,
  adminPostToX,
  adminRevertOptimizationAction,
  adminRunContentOptimization,
  adminRunMigrationCleanTitles,
  adminRunUpdate,
  adminSendDailyReport,
  adminSendPriceAlerts,
  Product,
} from "@/lib/api";
import { useAdminAuth } from "@/lib/adminAuth";
import AiTeamDashboard from "@/components/AiTeamDashboard";
import LiveJobDashboard from "@/components/LiveJobDashboard";

const OPTIMIZATION_ACTION_LABELS: Record<string, string> = {
  rewrite_product: "商品説明のリライト",
  new_guide: "新規ガイド作成",
  reorder_homepage: "トップページ注目商品の入れ替え",
};

const OPPORTUNITY_GOAL_LABELS: Record<string, string> = {
  search_ctr: "検索結果での訴求（SEO）",
  on_page_conversion: "ページ上の購入訴求（CRO）",
};

const OPTIMIZATION_STATUS_LABELS: Record<string, string> = {
  applied: "実施済み",
  reverted: "元に戻し済み",
  failed: "失敗",
};

export default function AdminDashboard() {
  const { token } = useAdminAuth();
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [xPostPreview, setXPostPreview] = useState<string | null | undefined>(undefined);
  const [xCopyMessage, setXCopyMessage] = useState<string | null>(null);
  const [optimizationActions, setOptimizationActions] = useState<AiOptimizationAction[]>([]);
  const [opportunities, setOpportunities] = useState<ImprovementOpportunity[]>([]);

  const load = async () => {
    if (!token) return;
    const data = await adminListProducts(token);
    setProducts(data);
    setLoading(false);
  };

  const loadOptimizationActions = async () => {
    if (!token) return;
    try {
      const [actions, opps] = await Promise.all([
        adminListOptimizationActions(token),
        adminGetImprovementOpportunities(token),
      ]);
      setOptimizationActions(actions);
      setOpportunities(opps);
    } catch {
      // best-effort - the rest of the dashboard still works without this
    }
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
    adminGetXPostPreview(token)
      .then((result) => {
        if (!ignore) setXPostPreview(result.text);
      })
      .catch(() => {
        if (!ignore) setXPostPreview(null);
      });
    adminListOptimizationActions(token)
      .then((data) => {
        if (!ignore) setOptimizationActions(data);
      })
      .catch(() => {
        // best-effort
      });
    adminGetImprovementOpportunities(token)
      .then((data) => {
        if (!ignore) setOpportunities(data);
      })
      .catch(() => {
        // best-effort
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

  const handleFetchRakuten = async () => {
    if (!token) return;
    setBusy(true);
    setMessage(null);
    try {
      const result = await adminFetchRakuten(token);
      setMessage(
        `楽天価格取得完了: 更新${result.prices_updated}件 / 見つからず${result.prices_skipped}件 / ` +
          `新規発見${result.products_discovered}件（安全な商品は自動公開、それ以外は承認待ちに追加） / AI再生成${result.ai_regenerated}件`
      );
      await load();
    } catch (err) {
      setMessage(
        `取得失敗: ${err instanceof Error ? err.message : String(err)}（RAKUTEN_APP_IDが設定されているか確認してください）`
      );
    } finally {
      setBusy(false);
    }
  };

  const handleBackfillImages = async () => {
    if (!token) return;
    setBusy(true);
    setMessage("商品画像を確認・補完しています（商品数によっては数分かかります）...");
    try {
      const r = await adminBackfillImages(token);
      const missing =
        r.still_missing.length > 0
          ? ` / 見つからず${r.still_missing.length}件（${r.still_missing.slice(0, 10).join("、")}${r.still_missing.length > 10 ? " ほか" : ""}）`
          : " / 画像の無い商品は0件です";
      setMessage(
        `商品画像の補完完了: 確認${r.checked}件 / リンク切れ${r.broken_found}件 / ` +
          `楽天から${r.filled_from_rakuten}件・Yahoo!から${r.filled_from_yahoo}件を補完${missing}` +
          (r.yahoo_quota_exhausted ? "（Yahoo!の1日の利用上限に達したため、残りは楽天のみで検索しました）" : "")
      );
      await load();
    } catch (err) {
      setMessage(`補完失敗: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setBusy(false);
    }
  };

  const handleSendPriceAlerts = async () => {
    if (!token) return;
    setBusy(true);
    setMessage(null);
    try {
      const result = await adminSendPriceAlerts(token);
      setMessage(
        `値下がり通知の送信完了: 送信${result.price_alerts_sent}件 / スキップ${result.price_alerts_skipped}件`
      );
    } catch (err) {
      setMessage(
        `送信失敗: ${err instanceof Error ? err.message : String(err)}（RESEND_API_KEYが設定されているか確認してください）`
      );
    } finally {
      setBusy(false);
    }
  };

  const handleSendDailyReport = async () => {
    if (!token) return;
    setBusy(true);
    setMessage(null);
    try {
      await adminSendDailyReport(token);
      setMessage("本日のAI会議レポートを送信しました。");
    } catch (err) {
      setMessage(
        `送信失敗: ${err instanceof Error ? err.message : String(err)}（DAILY_REPORT_EMAILが設定されているか確認してください）`
      );
    } finally {
      setBusy(false);
    }
  };

  const handlePostToX = async () => {
    if (!token) return;
    setBusy(true);
    setMessage(null);
    try {
      const result = await adminPostToX(token);
      setMessage(
        `X投稿完了: 投稿${result.x_posts_sent}件 / スキップ${result.x_posts_skipped}件` +
          "（無料APIプランでは投稿がスキップされ、下の「手動投稿用テキスト」からコピペしていただく運用になっています）"
      );
    } catch (err) {
      setMessage(
        `投稿失敗: ${err instanceof Error ? err.message : String(err)}（X_API_KEY等が設定されているか確認してください）`
      );
    } finally {
      setBusy(false);
    }
  };

  const handleCopyXPost = async () => {
    if (!xPostPreview) return;
    try {
      await navigator.clipboard.writeText(xPostPreview);
      setXCopyMessage("コピーしました。");
    } catch {
      setXCopyMessage("コピーに失敗しました。テキストを選択して手動でコピーしてください。");
    }
  };

  const handleRunContentOptimization = async () => {
    if (!token) return;
    setBusy(true);
    setMessage(null);
    try {
      const result = await adminRunContentOptimization(token);
      setMessage(
        `AI自動改善を実行しました: 実施${result.actions_applied}件 / 効果測定${result.actions_evaluated}件` +
          (result.actions_auto_reverted > 0 ? ` / 悪化のため自動で元に戻した変更${result.actions_auto_reverted}件` : "")
      );
      await loadOptimizationActions();
    } catch (err) {
      setMessage(`実行失敗: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setBusy(false);
    }
  };

  const handleRevertAction = async (actionId: number) => {
    if (!token) return;
    const confirmed = window.confirm("この変更を元に戻します（変更前の紹介文に戻します）。よろしいですか？");
    if (!confirmed) return;
    setBusy(true);
    setMessage(null);
    try {
      await adminRevertOptimizationAction(token, actionId);
      setMessage("変更を元に戻しました。");
      await loadOptimizationActions();
      await load();
    } catch (err) {
      setMessage(`元に戻す処理に失敗: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setBusy(false);
    }
  };

  const handleDiscover = async () => {
    if (!token) return;
    setBusy(true);
    setMessage(null);
    try {
      const result = await adminDiscoverProducts(token);
      setMessage(
        `商品自動検出完了: 候補${result.candidates_considered}件を確認 / 新規${result.products_discovered}件を追加` +
          "（安全な商品は自動公開、際どい商品は承認待ちとして追加 - 商品管理ページで内容を確認してください）"
      );
      await load();
    } catch (err) {
      setMessage(
        `検出失敗: ${err instanceof Error ? err.message : String(err)}（RAKUTEN_APP_IDが設定されているか確認してください）`
      );
    } finally {
      setBusy(false);
    }
  };

  const handleCleanTitles = async () => {
    if (!token) return;
    const confirmed = window.confirm(
      "商品名のクレンジングと重複統合を実行します。宣伝文句を取り除いた名前に更新し、" +
        "同じ型番と判定された商品は1つに統合（片方は削除）されます。実況ダッシュボードで進行状況を確認できます。\n\n" +
        "実行しますか？"
    );
    if (!confirmed) return;
    setBusy(true);
    setMessage(null);
    try {
      const result = await adminRunMigrationCleanTitles(token, false);
      setMessage(
        `商品名クレンジング完了: 対象${result.products_checked}件 / リネーム${result.renamed}件 / ` +
          `統合${result.merge_groups}グループ（${result.products_merged}件を統合）`
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
      <h1 className="font-display text-xl font-semibold text-foreground">ダッシュボード</h1>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
        <StatCard label="商品数" value={products.length} />
        <StatCard label="強い買い時" value={byScore.strong_buy ?? 0} />
        <StatCard label="買い時" value={byScore.buy ?? 0} />
        <StatCard label="様子見" value={byScore.neutral ?? 0} />
        <StatCard label="判定不能" value={byScore.insufficient_data ?? 0} />
      </div>

      <AiTeamDashboard token={token} />

      <LiveJobDashboard token={token} />

      <div className="flex flex-col gap-3 rounded-2xl border border-border bg-card p-5">
        <h2 className="font-display font-medium text-foreground">価格CSVインポート</h2>
        <p className="text-sm text-foreground/50">
          product_name,brand,category,model_number,price,product_url,image_url の列を持つCSVを取り込みます。
          任意列（msrp,release_date,skill_level,performance_type,is_current_generation）を追加すると、新規商品の定価・発売日・ポジショニング情報も同時に設定できます（既存商品には影響しません）。
        </p>
        <input type="file" accept=".csv" onChange={handleCsv} disabled={busy} className="text-sm" />
      </div>

      <div className="flex flex-col gap-3 rounded-2xl border border-border bg-card p-5">
        <h2 className="font-display font-medium text-foreground">楽天市場から価格取得</h2>
        <p className="text-sm text-foreground/50">
          全商品を楽天市場で検索し、最新価格を自動取得します。毎日の自動更新（GitHub Actions）と同じ処理を
          今すぐ手動で実行できます。RAKUTEN_APP_ID が設定されている必要があります。
        </p>
        <button
          onClick={handleFetchRakuten}
          disabled={busy}
          className="w-fit rounded-full bg-brand px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
        >
          今すぐ価格を取得
        </button>
      </div>

      <div className="flex flex-col gap-3 rounded-2xl border border-border bg-card p-5">
        <h2 className="font-display font-medium text-foreground">商品画像の補完（NO IMAGEの解消）</h2>
        <p className="text-sm text-foreground/50">
          画像が無い・無効（空欄や見本の example.com など）・リンク切れの商品について、楽天市場（見つからなければYahoo!ショッピング）で
          同じ商品と判定できる出品の写真を取得して設定します。価格取得と同じ「アクセサリではないか・価格が妥当か」の判定を通った出品だけを使い、
          価格は記録しません。毎朝の自動更新でも同じ補完が行われます。
        </p>
        <button
          onClick={handleBackfillImages}
          disabled={busy}
          className="w-fit rounded-full bg-brand px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
        >
          今すぐ画像を補完
        </button>
      </div>

      <div className="flex flex-col gap-3 rounded-2xl border border-border bg-card p-5">
        <h2 className="font-display font-medium text-foreground">商品の自動検出</h2>
        <p className="text-sm text-foreground/50">
          楽天市場をカテゴリ別に検索し、まだ登録されていない商品の候補を追加します。中古・付属品等のNGワードを含まず、
          価格も妥当な範囲（クラブ類は1万円以上、ボールは3千円以上）の商品は自動的に公開されます。それ以外（際どい商品）は
          従来通り「承認待ち」として追加され、サイトには公開されません。誤った商品が混ざることがあるため、
          商品管理ページで内容を定期的に確認してください。毎日の自動更新でも実行されます。
        </p>
        <button
          onClick={handleDiscover}
          disabled={busy}
          className="w-fit rounded-full bg-brand px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
        >
          今すぐ検出
        </button>
      </div>

      <div className="flex flex-col gap-3 rounded-2xl border border-border bg-card p-5">
        <h2 className="font-display font-medium text-foreground">既存商品データの大掃除（型番統合）</h2>
        <p className="text-sm text-foreground/50">
          ショップ独自の宣伝文句（「【送料無料】」「ポイント10倍」等）を取り除いた「ブランド＋型番」のきれいな
          商品名に整形します。同じ型番と判定された商品は1つに統合（価格履歴等は残る側に引き継がれ、
          もう一方は削除）されます。Renderの無料プランにはシェル機能が無いため、この管理画面のボタンから
          `scripts/migrate_clean_titles.py` と同じ処理を実行できるようにしたものです。
        </p>
        <button
          onClick={handleCleanTitles}
          disabled={busy}
          className="w-fit rounded-full bg-brand px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
        >
          大掃除を実行
        </button>
      </div>

      <div className="flex flex-col gap-3 rounded-2xl border border-border bg-card p-5">
        <h2 className="font-display font-medium text-foreground">分析・AI説明文の再生成</h2>
        <p className="text-sm text-foreground/50">
          全商品の買い時判定を再計算し、価格が変化した商品のみAI説明文を再生成します。
        </p>
        <button
          onClick={handleRunUpdate}
          disabled={busy}
          className="w-fit rounded-full bg-brand px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
        >
          今すぐ実行
        </button>
      </div>

      <div className="flex flex-col gap-3 rounded-2xl border border-border bg-card p-5">
        <h2 className="font-display font-medium text-foreground">値下がり通知メールを送信</h2>
        <p className="text-sm text-foreground/50">
          目標価格に到達した未通知のアラートにメールを送信します（Resend経由）。毎日の自動更新でも実行されます。
          RESEND_API_KEY が設定されている必要があります。
        </p>
        <button
          onClick={handleSendPriceAlerts}
          disabled={busy}
          className="w-fit rounded-full bg-brand px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
        >
          今すぐ送信
        </button>
      </div>

      <div className="flex flex-col gap-3 rounded-2xl border border-border bg-card p-5">
        <h2 className="font-display font-medium text-foreground">本日のAI会議レポートを送信</h2>
        <p className="text-sm text-foreground/50">
          直近24時間の新商品・価格取得結果、アフィリエイトクリック数の前日比、エラー・警告状況、検索流入を実データのみでまとめた日本語レポートをメール送信します（Resend経由）。
          毎日の自動更新の最後にも実行されます。DAILY_REPORT_EMAIL・RESEND_API_KEY が設定されている必要があります。
        </p>
        <button
          onClick={handleSendDailyReport}
          disabled={busy}
          className="w-fit rounded-full bg-brand px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
        >
          今すぐ送信
        </button>
      </div>

      <div className="flex flex-col gap-3 rounded-2xl border border-border bg-card p-5">
        <h2 className="font-display font-medium text-foreground">今日のお買い得情報をXに投稿</h2>
        <p className="text-sm text-foreground/50">
          買い時スコアが高い商品（データ不足の場合は定価からの割引率）を1〜2点選び、AIが紹介文を生成します。
          X APIの無料プランでは投稿自体ができなくなった（402エラー）ため、現在は下のテキストを手動でコピーして
          Xに貼り付けて投稿する運用です。毎朝のAI会議レポートにも同じテキストが含まれます。
        </p>

        <div className="flex flex-col gap-2">
          <p className="text-xs font-medium uppercase tracking-wide text-foreground/40">
            手動投稿用テキストのプレビュー
          </p>
          {xPostPreview === undefined ? (
            <p className="text-sm text-foreground/50">読み込み中...</p>
          ) : xPostPreview === null ? (
            <p className="text-sm text-foreground/50">
              本日は投稿対象となる商品がありません（強い買い時シグナルの商品も、定価割引の商品もまだ無し）。
            </p>
          ) : (
            <>
              <textarea
                readOnly
                value={xPostPreview}
                rows={5}
                className="w-full resize-none rounded-xl border border-border bg-background p-3 text-sm text-foreground"
              />
              <div className="flex items-center gap-3">
                <button
                  onClick={handleCopyXPost}
                  className="w-fit rounded-full border border-border px-4 py-2 text-sm font-semibold text-foreground"
                >
                  コピー
                </button>
                {xCopyMessage && <p className="text-xs text-foreground/50">{xCopyMessage}</p>}
              </div>
            </>
          )}
        </div>

        <button
          onClick={handlePostToX}
          disabled={busy}
          className="w-fit rounded-full bg-brand px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
        >
          今すぐ投稿（API経由・無料プランでは失敗します）
        </button>
      </div>

      <div className="flex flex-col gap-3 rounded-2xl border border-border bg-card p-5">
        <h2 className="font-display font-medium text-foreground">AI自動改善ループ（STEP42）</h2>
        <p className="text-sm text-foreground/50">
          実際のGA4/Search Console/クリックデータをもとに、AIが商品説明のリライトや新規ガイド記事の作成、
          トップページの注目商品入れ替えを自動で行います。何を・なぜ変更したか、後日の効果測定結果まで、
          すべて下の一覧に記録されます。毎日の自動更新の最後にも実行されます（記事生成にはClaude APIの実費用が発生し、
          1日あたり数件までに制限されています）。
        </p>
        <button
          onClick={handleRunContentOptimization}
          disabled={busy}
          className="w-fit rounded-full bg-brand px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
        >
          今すぐ実行
        </button>

        <div className="mt-2 flex flex-col gap-2">
          <p className="text-xs font-medium uppercase tracking-wide text-foreground/40">
            優先度の高い改善機会（実データから算出・次回の実行で上位から自動改善）
          </p>
          {opportunities.length === 0 ? (
            <p className="text-sm text-foreground/50">
              現時点で、実データ上の明確な改善余地が見つかった商品ページはありません（データ蓄積中の場合もあります）。
            </p>
          ) : (
            <ol className="flex flex-col gap-2">
              {opportunities.slice(0, 5).map((o, i) => (
                <li key={o.product_id} className="rounded-xl border border-border bg-background p-3 text-sm">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-semibold text-foreground">{i + 1}.</span>
                    <span className="font-medium text-foreground">{o.product_name}</span>
                    <span className="rounded-full border border-border px-2 py-0.5 text-xs text-foreground/60">
                      {OPPORTUNITY_GOAL_LABELS[o.goal] ?? o.goal}
                    </span>
                  </div>
                  <p className="mt-1 text-foreground/65">{o.decision_basis}</p>
                </li>
              ))}
            </ol>
          )}
        </div>

        <p className="mt-2 text-xs font-medium uppercase tracking-wide text-foreground/40">実施履歴</p>
        {optimizationActions.length === 0 ? (
          <p className="text-sm text-foreground/50">まだ実行記録がありません。</p>
        ) : (
          <div className="mt-2 flex flex-col gap-3">
            {optimizationActions.map((action) => (
              <div key={action.id} className="rounded-xl border border-border bg-background p-4 text-sm">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded-full border border-border px-2 py-0.5 text-xs font-medium text-foreground/60">
                    {OPTIMIZATION_ACTION_LABELS[action.action_type] ?? action.action_type}
                  </span>
                  <span className="text-xs text-foreground/40">{action.target_path}</span>
                  <span
                    className={`text-xs font-medium ${
                      action.status === "failed" ? "text-red-600" : "text-foreground/50"
                    }`}
                  >
                    {action.status === "reverted" && action.revert_reason === "auto_worse"
                      ? "自動で元に戻し済み"
                      : (OPTIMIZATION_STATUS_LABELS[action.status] ?? action.status)}
                  </span>
                  <span className="text-xs text-foreground/40">
                    {new Date(action.created_at).toLocaleString("ja-JP")}
                  </span>
                </div>
                <p className="mt-2 text-foreground/70">判断根拠: {action.decision_basis}</p>
                {action.effect_summary && (
                  <p className="mt-1 text-foreground/70">
                    効果測定:{" "}
                    <span
                      className={
                        action.effect_verdict === "improved"
                          ? "font-medium text-signal-high"
                          : action.effect_verdict === "worse"
                            ? "font-medium text-red-600"
                            : "text-foreground/60"
                      }
                    >
                      {action.effect_summary}
                    </span>
                  </p>
                )}
                {action.action_type === "rewrite_product" && action.status === "applied" && (
                  <button
                    onClick={() => handleRevertAction(action.id)}
                    disabled={busy}
                    className="mt-2 w-fit rounded-full border border-border px-3 py-1.5 text-xs font-semibold text-foreground/70 disabled:opacity-50"
                  >
                    この変更を元に戻す
                  </button>
                )}
                {action.status === "reverted" && (
                  <p className="mt-2 text-xs text-foreground/40">
                    {action.revert_reason === "auto_worse"
                      ? "効果測定で悪化と判定したため、AIが自動で元に戻し、最新の価格データで通常の文面に再生成しました。"
                      : "元に戻し済みです。"}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {message && <p className="text-sm text-foreground/70">{message}</p>}
      {loading && <p className="text-sm text-foreground/50">読み込み中...</p>}
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-2xl border border-border bg-card p-4">
      <div className="text-xs text-foreground/50">{label}</div>
      <div className="font-display text-2xl font-semibold text-foreground">{value}</div>
    </div>
  );
}
