"use client";

import { useEffect, useRef, useState } from "react";

import {
  AffiliateClickRecent,
  AffiliateClickSummary,
  AiOptimizationAction,
  ErrorLog,
  ImprovementOpportunity,
  PageStat,
  adminAutoFixLogs,
  adminFetchRakuten,
  adminGetAffiliateClickSummary,
  adminGetImprovementOpportunities,
  adminGetLogs,
  adminGetTopPages,
  adminListOptimizationActions,
} from "@/lib/api";
import { useLiveJobUpdates, type LiveJobStage } from "@/lib/useLiveJobUpdates";

// Every chat bubble, status, and metric in this component is derived from
// a real backend event or a real aggregate number - the same SSE stream
// (app/progress.py) and ErrorLog/AffiliateClick tables that already power
// 実況ダッシュボード, /admin/logs, and the click-tracking endpoint added
// alongside this component. The "AI会議" framing is a presentation layer
// over real data (persona-narrated real facts, rule-based recommendations
// derived from real thresholds) - it never invents a log line, a click, a
// pageview, or a conclusion. See docs/ai_company_guidelines.md's standing
// anti-fabrication rule, which applies to this internal admin page too.

type PersonaId = "ceo" | "cmo" | "cro" | "cpo" | "cso" | "editor" | "compliance";
type Status = "THINKING" | "ANALYZING" | "SYNCING" | "IDLE";

interface Persona {
  id: PersonaId;
  role: string;
  title: string;
  focus: string;
  icon: string;
  stages: string[];
}

const PERSONAS: Persona[] = [
  { id: "ceo", role: "CEO", title: "President AI", focus: "全体方針・PDCA統括", icon: "👔", stages: [] },
  {
    id: "cso",
    role: "CSO",
    title: "Strategy AI",
    focus: "新商品探索・競合トレンド分析",
    icon: "🔍",
    stages: ["discovery", "popularity"],
  },
  {
    id: "cro",
    role: "CRO",
    title: "Revenue AI",
    focus: "クリック分析・CVR向上",
    icon: "📈",
    stages: ["rakuten_prices", "yahoo_prices", "price_alerts"],
  },
  {
    id: "cpo",
    role: "CPO",
    title: "Product AI",
    focus: "データ品質・システム改善",
    icon: "🛠️",
    stages: ["analysis", "title_cleanup"],
  },
  { id: "cmo", role: "CMO", title: "Marketing AI", focus: "SEO・検索流入分析", icon: "📢", stages: ["x_post"] },
  // Editor/Compliance own no daily-batch stage of their own (guide content
  // and PR-表記/価格表記 review aren't automated steps) - they stay IDLE
  // outside the planning session and real-time log/discovery reactions
  // below, rather than faking an ANALYZING state with nothing real behind
  // it (see this file's anti-fabrication note above).
  { id: "editor", role: "Editor", title: "Content AI", focus: "ガイド記事企画・コンテンツ品質", icon: "✍️", stages: [] },
  {
    id: "compliance",
    role: "Compliance",
    title: "Legal & Policy AI",
    focus: "ASP規約・PR表記・価格表記チェック",
    icon: "⚖️",
    stages: [],
  },
];

const SHOP_LABELS: Record<string, string> = {
  amazon: "Amazon",
  rakuten: "楽天",
  yahoo: "Yahoo!",
  official: "公式サイト",
};

const OPTIMIZATION_ACTION_SHORT_LABELS: Record<string, string> = {
  rewrite_product: "商品説明リライト",
  new_guide: "新規ガイド作成",
  reorder_homepage: "注目商品の入れ替え",
};

const CLICK_POLL_INTERVAL_MS = 10000;
const DEPLOYING_DURATION_MS = 2500;
const MEETING_STEP_DELAY_MS = 1100;
const THINKING_BEFORE_MESSAGE_MS = 650;

interface ChatMessage {
  id: string;
  persona: PersonaId;
  text: string;
  timestamp: number;
  fresh: boolean;
}

function personaForStage(stageId: string): PersonaId {
  for (const p of PERSONAS) {
    if (p.stages.includes(stageId)) return p.id;
  }
  return "ceo";
}

function formatTime(ts: number): string {
  return new Date(ts).toLocaleTimeString("ja-JP", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function stageLogText(stage: LiveJobStage, phase: "start" | "done"): string {
  if (phase === "start") return `${stage.label}...`;
  return stage.detail ? `${stage.label} 完了 - ${stage.detail}` : `${stage.label} 完了`;
}

function sourceToPersona(source: string): PersonaId {
  switch (source) {
    case "discovery":
    case "popularity":
      return "cso";
    case "price_fetch":
    case "price_alert_email":
      return "cro";
    case "analysis":
    case "csv_import":
    case "title_migration":
      return "cpo";
    case "x_post":
      return "cmo";
    default:
      return "ceo";
  }
}

// A rule-based ("振り返り→課題特定→改善施策") planning session over real
// data snapshots - never an LLM call (no cost, no risk of an invented
// number). Every line either quotes a real value directly or applies a
// simple, stated threshold to one.
function buildPlanningSession(data: {
  clicks: AffiliateClickSummary | null;
  logs: ErrorLog[];
  topPages: PageStat[] | null;
  optimizationActions: AiOptimizationAction[] | null;
  opportunities: ImprovementOpportunity[] | null;
}): { persona: PersonaId; lines: string[] }[] {
  const steps: { persona: PersonaId; lines: string[] }[] = [];

  const dailyJobLog = data.logs.find((l) => l.source === "daily_job");
  steps.push({
    persona: "cso",
    lines: dailyJobLog
      ? [`振り返り: 最新の日次実行ログは「${dailyJobLog.message}」でした。`]
      : ["振り返り: まだ日次実行の記録がありません。次回の自動実行後にトレンドを分析します。"],
  });

  const total = data.clicks?.total ?? 0;
  if (!data.clicks || total === 0) {
    steps.push({
      persona: "cro",
      lines: ["振り返り: アフィリエイトクリックの記録がまだありません。計測を開始したばかりです。"],
    });
  } else {
    const sorted = [...data.clicks.by_shop].sort((a, b) => b.count - a.count);
    const lines = [
      `振り返り: 直近のクリック合計は${total}件です（内訳: ${sorted
        .map((s) => `${SHOP_LABELS[s.shop] ?? s.shop} ${s.count}件`)
        .join(" / ")}）。`,
    ];
    if (sorted.length >= 2 && sorted[0].count >= sorted[sorted.length - 1].count * 2) {
      lines.push(
        `課題特定: ${SHOP_LABELS[sorted[0].shop] ?? sorted[0].shop}への偏りが大きいです。他ショップの表示順・訴求文言の見直しが有効そうです。`
      );
    }
    const top = data.clicks.top_products[0];
    if (top) lines.push(`最もクリックされている商品は「${top.product_name}」（${top.clicks}件）でした。`);
    steps.push({ persona: "cro", lines });
  }

  if (data.topPages && data.topPages.length > 0) {
    const top = data.topPages[0];
    steps.push({
      persona: "cmo",
      lines: [`振り返り: 直近28日で最もPVが多いページは「${top.path}」（${top.pageviews}PV）でした。`],
    });
  } else {
    steps.push({
      persona: "cmo",
      lines: ["振り返り: GA4が未設定のため検索流入データは確認できません。設定後に上位ページ分析が可能になります。"],
    });
  }

  // STEP43: the same revenue-ranked priority queue the daily optimization
  // run spends its budget on (app/content_optimizer.py
  // find_improvement_opportunities) - CMO owns search-result (SEO) gaps,
  // CRO owns on-page conversion gaps. Each line quotes the real basis.
  const topSearchGap = (data.opportunities ?? []).find((o) => o.goal === "search_ctr");
  const topConversionGap = (data.opportunities ?? []).find((o) => o.goal === "on_page_conversion");
  if (topSearchGap) {
    steps.push({
      persona: "cmo",
      lines: [`課題特定（SEO）: 「${topSearchGap.product_name}」— ${topSearchGap.decision_basis}`],
    });
  }
  if (topConversionGap) {
    steps.push({
      persona: "cro",
      lines: [`課題特定（CRO）: 「${topConversionGap.product_name}」— ${topConversionGap.decision_basis}`],
    });
  }

  const errorCount = data.logs.filter((l) => l.level === "error").length;
  steps.push({
    persona: "cpo",
    lines:
      errorCount > 0
        ? [`課題特定: 直近のログに${errorCount}件のエラーがあります。商品管理・ログページでの確認をおすすめします。`]
        : ["振り返り: 直近のログにエラーは見当たりません。パイプラインは安定稼働中です。"],
  });

  // Editor reads the same daily_job summary line CSO already quoted above,
  // just for its own content-planning angle (real "新商品発見N件" count,
  // never a separate/invented number).
  const discoveredMatch = dailyJobLog?.message.match(/新商品発見(\d+)件/);
  const discoveredCount = discoveredMatch ? parseInt(discoveredMatch[1], 10) : null;
  const editorLines: string[] = [
    discoveredCount !== null && discoveredCount > 0
      ? `振り返り: 直近の自動実行で新たに${discoveredCount}件の商品が追加されました。関連ブランド・カテゴリのガイド記事更新を検討しましょう。`
      : "振り返り: 新着商品はまだありません。既存ガイド記事の鮮度を確認しておきます。",
  ];

  // STEP42: app/content_optimizer.py's autonomous decisions - real actions
  // it actually took (with their real decision basis) and any effect
  // measurements that just came in, never a summary invented from nothing.
  const dayAgo = Date.now() - 24 * 60 * 60 * 1000;
  const recentActions = (data.optimizationActions ?? []).filter((a) => new Date(a.created_at).getTime() >= dayAgo);
  if (recentActions.length > 0) {
    editorLines.push(
      `振り返り: 本日のAI自動改善は${recentActions.length}件です（` +
        recentActions.map((a) => `${OPTIMIZATION_ACTION_SHORT_LABELS[a.action_type] ?? a.action_type}: ${a.target_path}`).join("、") +
        "）。判断根拠と結果は管理画面の「AI自動改善ループ」で確認できます。"
    );
  }
  const recentlyEvaluated = (data.optimizationActions ?? []).filter(
    (a) => a.effect_evaluated_at && new Date(a.effect_evaluated_at).getTime() >= dayAgo
  );
  if (recentlyEvaluated.length > 0) {
    const worse = recentlyEvaluated.filter((a) => a.effect_verdict === "worse");
    editorLines.push(
      `効果測定: 過去の自動改善${recentlyEvaluated.length}件の効果測定が完了しました${
        worse.length > 0 ? `（うち${worse.length}件は悪化 - 元に戻すか見直しを検討してください）` : "。"
      }`
    );
  }

  steps.push({ persona: "editor", lines: editorLines });

  // Compliance reads price_fetch's own "warning"-level rows - the exact
  // real log lines pipeline.py already writes when a Rakuten/Yahoo match
  // looks like an accessory or its price deviates too far from the known
  // reference (see app/pipeline.py's _looks_like_accessory/_is_plausible_price).
  const priceWarnings = data.logs.filter((l) => l.level === "warning" && l.source === "price_fetch").length;
  steps.push({
    persona: "compliance",
    lines:
      priceWarnings > 0
        ? [
            `課題特定: 直近のログに価格表示の警告が${priceWarnings}件あります（アクセサリ誤検出・参考価格との乖離など）。表示価格の正確性を優先して確認しましょう。`,
          ]
        : ["振り返り: 価格表示に関する警告は見当たりません。表示価格の正確性は保たれています。"],
  });

  const actions: string[] = [];
  if (!data.clicks || total === 0) {
    actions.push("クリック計測が始まったばかりです。数日データを蓄積してから傾向を評価しましょう。");
  } else {
    const seenShops = new Set(data.clicks.by_shop.map((s) => s.shop));
    const missing = (["amazon", "rakuten", "yahoo"] as const).filter((s) => !seenShops.has(s));
    if (missing.length > 0) {
      actions.push(
        `${missing.map((s) => SHOP_LABELS[s]).join("・")}へのクリックが未記録です。リンクの表示位置・視認性を確認しましょう。`
      );
    }
  }
  const topOpportunity = (data.opportunities ?? [])[0];
  if (topOpportunity) {
    actions.push(
      `想定報酬インパクトが最も大きい「${topOpportunity.product_name}」から、次回の自動改善ループで優先的に改善します。`
    );
  }
  if (errorCount > 0) actions.push("エラーログの内容を確認し、原因を特定しましょう。");
  if (priceWarnings > 0) actions.push("価格表示の警告（price_fetch）の内容を確認し、表示価格の正確性を優先しましょう。");
  if (!data.topPages) actions.push("GA4を設定すると、検索流入・特集ページのインデックス状況も分析対象にできます。");
  if (actions.length === 0) actions.push("現状、緊急の課題は見当たりません。引き続きデータを蓄積し、次回再評価します。");

  steps.push({ persona: "ceo", lines: ["改善施策: 各担当の報告を踏まえた次のアクションです。", ...actions] });

  return steps;
}

function StatusPulse({ status }: { status: Status }) {
  const meta: Record<Status, { color: string; label: string; pulse: boolean }> = {
    THINKING: { color: "bg-accent-dark", label: "THINKING", pulse: true },
    ANALYZING: { color: "bg-brand", label: "ANALYZING", pulse: true },
    SYNCING: { color: "bg-signal-mid", label: "SYNCING", pulse: true },
    IDLE: { color: "bg-foreground/25", label: "IDLE", pulse: false },
  };
  const m = meta[status];
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={`relative flex h-2 w-2 shrink-0 rounded-full ${m.color}`}>
        {m.pulse && <span className={`absolute inset-0 animate-ping rounded-full ${m.color} opacity-75`} />}
      </span>
      <span className="text-[10px] font-semibold uppercase tracking-widest text-foreground/60">{m.label}</span>
    </span>
  );
}

function PersonaCard({ persona, status }: { persona: Persona; status: Status }) {
  return (
    <div
      className={`flex flex-col gap-2 rounded-2xl border p-3 transition-colors ${
        status !== "IDLE" ? "border-brand/40 bg-brand/5" : "border-border bg-card"
      }`}
    >
      <div className="flex items-center justify-between">
        <span className="text-xl" aria-hidden>
          {persona.icon}
        </span>
        <StatusPulse status={status} />
      </div>
      <div>
        <p className="font-display text-sm font-semibold text-foreground">
          {persona.role} <span className="font-normal text-foreground/40">({persona.title})</span>
        </p>
        <p className="mt-0.5 text-[11px] text-foreground/50">{persona.focus}</p>
      </div>
    </div>
  );
}

function ShopBars({ byShop }: { byShop: AffiliateClickSummary["by_shop"] }) {
  const max = Math.max(1, ...byShop.map((s) => s.count));
  return (
    <div className="flex flex-col gap-2">
      {(["amazon", "rakuten", "yahoo", "official"] as const).map((shop) => {
        const count = byShop.find((s) => s.shop === shop)?.count ?? 0;
        return (
          <div key={shop} className="flex items-center gap-2 text-xs">
            <span className="w-16 shrink-0 text-foreground/60">{SHOP_LABELS[shop]}</span>
            <div className="h-2 flex-1 overflow-hidden rounded-full bg-background">
              <div
                className="h-full rounded-full bg-brand transition-[width] duration-500"
                style={{ width: `${(count / max) * 100}%` }}
              />
            </div>
            <span className="w-8 shrink-0 text-right font-semibold text-foreground">{count}</span>
          </div>
        );
      })}
    </div>
  );
}

export default function AiTeamDashboard({ token }: { token: string | null }) {
  const { run } = useLiveJobUpdates(token);
  const [clicks, setClicks] = useState<AffiliateClickSummary | null>(null);
  const [topPages, setTopPages] = useState<PageStat[] | null>(null);
  const [ga4Configured, setGa4Configured] = useState(true); // optimistic until the first failed fetch
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [syncing, setSyncing] = useState(false);
  const [meetingRunning, setMeetingRunning] = useState(false);
  const [meetingThinking, setMeetingThinking] = useState<PersonaId | null>(null);
  const [busy, setBusy] = useState(false);
  const [runMessage, setRunMessage] = useState<string | null>(null);
  const [autoFixBusy, setAutoFixBusy] = useState(false);
  const [now, setNow] = useState(() => Date.now());

  const seenClickIdsRef = useRef<Set<number>>(new Set());
  const seenLogIdsRef = useRef<Set<number>>(new Set());
  const seededRef = useRef(false);
  const prevStagesRef = useRef<Map<string, LiveJobStage["status"]>>(new Map());
  const chatEndRef = useRef<HTMLDivElement>(null);
  const clicksRef = useRef<AffiliateClickSummary | null>(null);
  const logsRef = useRef<ErrorLog[]>([]);
  const topPagesRef = useRef<PageStat[] | null>(null);
  const optimizationActionsRef = useRef<AiOptimizationAction[] | null>(null);
  const opportunitiesRef = useRef<ImprovementOpportunity[] | null>(null);

  const addMessages = (additions: Omit<ChatMessage, "fresh">[]) => {
    if (additions.length === 0) return;
    setMessages((current) => [
      ...current.map((m) => ({ ...m, fresh: false })),
      ...additions.map((m) => ({ ...m, fresh: true })),
    ].slice(-80));
  };

  // Initial load: real logs (seed the timeline) + real click summary + a
  // best-effort GA4 pull (silently unavailable when not configured -
  // never shown as an error, since it's an optional integration).
  useEffect(() => {
    if (!token) return;
    Promise.all([
      adminGetLogs(token).catch(() => [] as ErrorLog[]),
      adminGetAffiliateClickSummary(token).catch(() => null),
      adminGetTopPages(token).catch(() => null),
      adminListOptimizationActions(token).catch(() => null),
      adminGetImprovementOpportunities(token).catch(() => null),
    ]).then(([logsData, clicksData, topPagesData, optimizationActionsData, opportunitiesData]) => {
      logsRef.current = logsData;
      seenLogIdsRef.current = new Set(logsData.map((l) => l.id));
      setClicks(clicksData);
      clicksRef.current = clicksData;
      if (clicksData) {
        seenClickIdsRef.current = new Set(clicksData.recent.map((c) => c.id));
      }
      setTopPages(topPagesData);
      topPagesRef.current = topPagesData;
      setGa4Configured(topPagesData !== null);
      optimizationActionsRef.current = optimizationActionsData;
      opportunitiesRef.current = opportunitiesData;

      if (!seededRef.current) {
        const seeded = [...logsData]
          .reverse()
          .slice(-15)
          .map((log) => ({
            id: `seed-${log.id}`,
            persona: sourceToPersona(log.source),
            text: log.message,
            timestamp: new Date(log.created_at).getTime(),
            fresh: false,
          }));
        setMessages(seeded);
        seededRef.current = true;
      }
    });
  }, [token]);

  // Poll the real click summary and the real error-log list. Any click id
  // not seen before becomes a real-time CRO reaction bubble; any new
  // warning/error-level log row becomes a real-time Compliance reaction
  // bubble ("エラー検知時の規約的観点からの指摘") - both grounded in the
  // exact real row, never a generated/invented event.
  useEffect(() => {
    if (!token) return;
    const poll = async () => {
      setSyncing(true);
      try {
        const [data, logsData] = await Promise.all([
          adminGetAffiliateClickSummary(token),
          adminGetLogs(token).catch(() => null),
        ]);
        setClicks(data);
        clicksRef.current = data;
        const newOnes = data.recent.filter((c) => !seenClickIdsRef.current.has(c.id));
        if (newOnes.length > 0 && seenClickIdsRef.current.size > 0) {
          const additions = newOnes
            .slice()
            .reverse()
            .map((c: AffiliateClickRecent) => ({
              id: `click-${c.id}`,
              persona: "cro" as PersonaId,
              text: `${SHOP_LABELS[c.shop] ?? c.shop}リンクのクリックを検知！${
                c.product_name ? `「${c.product_name}」` : "商品詳細"
              }への遷移です（${c.placement}）。`,
              timestamp: new Date(c.created_at).getTime(),
            }));
          addMessages(additions);
        }
        data.recent.forEach((c) => seenClickIdsRef.current.add(c.id));

        if (logsData) {
          logsRef.current = logsData;
          const newLogs = logsData.filter(
            (l) => !seenLogIdsRef.current.has(l.id) && (l.level === "warning" || l.level === "error")
          );
          if (newLogs.length > 0 && seenLogIdsRef.current.size > 0) {
            const additions = newLogs
              .slice()
              .reverse()
              .map((l) => ({
                id: `log-${l.id}`,
                persona: "compliance" as PersonaId,
                text: `${l.source}で${l.level === "warning" ? "警告" : "エラー"}を検知しました：「${
                  l.message.length > 60 ? `${l.message.slice(0, 60)}…` : l.message
                }」。規約・表示の観点から確認をおすすめします。`,
                timestamp: new Date(l.created_at).getTime(),
              }));
            addMessages(additions);
          }
          logsData.forEach((l) => seenLogIdsRef.current.add(l.id));
        }
      } catch {
        // best-effort - a failed poll just tries again next interval
      } finally {
        setSyncing(false);
      }
    };
    const id = setInterval(poll, CLICK_POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [token]);

  // Real pipeline stage transitions (see app/progress.py) become chat
  // bubbles from whichever persona owns that stage - identical data
  // source to 実況ダッシュボード, just persona-narrated.
  useEffect(() => {
    if (!run) return;
    const prev = prevStagesRef.current;
    const next = new Map<string, LiveJobStage["status"]>();
    const additions: Omit<ChatMessage, "fresh">[] = [];

    run.stages.forEach((stage, i) => {
      const key = `${stage.stage}-${i}`;
      next.set(key, stage.status);
      const prevStatus = prev.get(key);
      if (prevStatus === undefined) {
        additions.push({
          id: `${run.started_at}-${key}-start`,
          persona: personaForStage(stage.stage),
          text: stageLogText(stage, "start"),
          timestamp: Date.now(),
        });
      } else if (prevStatus === "running" && stage.status === "done") {
        additions.push({
          id: `${run.started_at}-${key}-done`,
          persona: personaForStage(stage.stage),
          text: stageLogText(stage, "done"),
          timestamp: Date.now(),
        });
        // Editor reacts to CSO's own real discovery count (same string,
        // "新規N件（候補M件中）" from app/routers/admin.py's finish_stage
        // call) with a content-planning angle, only when something was
        // actually found - never a message with nothing real behind it.
        if (stage.stage === "discovery" && stage.detail) {
          const match = stage.detail.match(/新規(\d+)件/);
          const count = match ? parseInt(match[1], 10) : 0;
          if (count > 0) {
            additions.push({
              id: `${run.started_at}-${key}-editor-reaction`,
              persona: "editor",
              text: `新たに${count}件の商品が追加されました。関連するガイド記事の更新を検討しましょう。`,
              timestamp: Date.now(),
            });
          }
        }
      }
    });

    prevStagesRef.current = next;
    addMessages(additions);
  }, [run]);

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 500);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, meetingThinking]);

  const statusFor = (persona: Persona): Status => {
    if (meetingThinking === persona.id) return "THINKING";
    const isRunning =
      !!run &&
      run.status === "running" &&
      (persona.id === "ceo" ? true : run.stage !== null && persona.stages.includes(run.stage));
    if (isRunning) return "ANALYZING";
    if (persona.id === "cro" && syncing) return "SYNCING";

    const lastFinished = [...messages].reverse().find((m) => m.persona === persona.id && m.text.includes("完了"));
    if (lastFinished && now - lastFinished.timestamp < DEPLOYING_DURATION_MS) return "ANALYZING";

    return "IDLE";
  };

  const runMeeting = async () => {
    if (meetingRunning) return;
    setMeetingRunning(true);
    addMessages([
      {
        id: `meeting-start-${Date.now()}`,
        persona: "ceo",
        text: "AI戦略会議を開始します。各担当、現状のデータを報告してください。",
        timestamp: Date.now(),
      },
    ]);

    const steps = buildPlanningSession({
      clicks: clicksRef.current,
      logs: logsRef.current,
      topPages: topPagesRef.current,
      optimizationActions: optimizationActionsRef.current,
      opportunities: opportunitiesRef.current,
    });
    for (const step of steps) {
      setMeetingThinking(step.persona);
      await new Promise((r) => setTimeout(r, THINKING_BEFORE_MESSAGE_MS));
      setMeetingThinking(null);
      addMessages(
        step.lines.map((line, i) => ({
          id: `meeting-${Date.now()}-${step.persona}-${i}`,
          persona: step.persona,
          text: line,
          timestamp: Date.now(),
        }))
      );
      await new Promise((r) => setTimeout(r, MEETING_STEP_DELAY_MS));
    }
    setMeetingRunning(false);
  };

  const handleRunAll = async () => {
    if (!token) return;
    const confirmed = window.confirm(
      "本番の日次バッチ処理（楽天/Yahoo価格取得・新商品探索・買い時再判定・値下がり通知・SNS投稿）を今すぐ実行します。" +
        "「今すぐ価格を取得」ボタンと全く同じ処理で、外部APIへの実際のリクエストが発生します。\n\n実行しますか？"
    );
    if (!confirmed) return;
    setBusy(true);
    setRunMessage(null);
    try {
      const result = await adminFetchRakuten(token);
      setRunMessage(
        `日次バッチ完了: 価格更新${result.prices_updated}件 / 新商品${result.products_discovered}件 / AI再生成${result.ai_regenerated}件`
      );
    } catch (err) {
      setRunMessage(`実行失敗: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setBusy(false);
    }
  };

  // CPO/Complianceの「AI自動修復」: 軽微な info/warning ログと3日以上前の
  // error ログを一括削除する（backend: crud.cleanup_error_logs）。外部APIは
  // 一切呼ばないので絶対ルール1の確認ダイアログは必須ではないが、削除操作
  // であることは変わらないため、他の削除系ボタンと同じ確認を挟む。
  const handleAutoFixLogs = async () => {
    if (!token) return;
    const confirmed = window.confirm(
      "軽微なログ（info/warning）と3日以上前のエラーログを一括削除します。直近3日以内のエラーログは残ります。\n\n実行しますか？"
    );
    if (!confirmed) return;
    setAutoFixBusy(true);
    try {
      const result = await adminAutoFixLogs(token);
      addMessages([
        {
          id: `auto-fix-${Date.now()}`,
          persona: "compliance",
          text: `AI自動修復を実行しました。削除: info ${result.deleted.info ?? 0}件 / warning ${
            result.deleted.warning ?? 0
          }件 / error ${result.deleted.error ?? 0}件（3日超）。残存エラー ${
            result.remaining_by_level.error ?? 0
          }件は直近3日以内のため保持しています。`,
          timestamp: Date.now(),
        },
      ]);
      const refreshed = await adminGetLogs(token).catch(() => null);
      if (refreshed) {
        logsRef.current = refreshed;
        seenLogIdsRef.current = new Set(refreshed.map((l) => l.id));
      }
    } catch (err) {
      addMessages([
        {
          id: `auto-fix-error-${Date.now()}`,
          persona: "compliance",
          text: `AI自動修復に失敗しました: ${err instanceof Error ? err.message : String(err)}`,
          timestamp: Date.now(),
        },
      ]);
    } finally {
      setAutoFixBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-border bg-card p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="font-display font-medium text-foreground">AI Executive War Room</h2>
          <p className="text-xs text-foreground/45">
            7人のAI社員が、実際のクリック・PV・パイプライン・ログデータをもとに会議しています。
          </p>
        </div>
        <div className="flex shrink-0 flex-wrap gap-2">
          <button
            type="button"
            onClick={runMeeting}
            disabled={meetingRunning}
            className="rounded-full border border-brand px-4 py-2.5 text-xs font-semibold text-brand disabled:opacity-50"
          >
            {meetingRunning ? "会議中..." : "AI戦略会議を開始"}
          </button>
          <button
            type="button"
            onClick={handleRunAll}
            disabled={busy || !token}
            className="rounded-full bg-brand px-4 py-2.5 text-xs font-semibold text-white disabled:opacity-50"
          >
            {busy ? "実行中..." : "全AIのPDCAサイクルを実行"}
          </button>
          <button
            type="button"
            onClick={handleAutoFixLogs}
            disabled={autoFixBusy || !token}
            title="⚖️ Compliance AI: 軽微なログを一括削除してシステム状態を正常化します"
            className="rounded-full border border-border px-4 py-2.5 text-xs font-semibold text-foreground/60 disabled:opacity-50"
          >
            {autoFixBusy ? "修復中..." : "⚖️ AI自動修復"}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-7">
        {PERSONAS.map((persona) => (
          <PersonaCard key={persona.id} persona={persona} status={statusFor(persona)} />
        ))}
      </div>

      {runMessage && <p className="text-xs text-foreground/60">{runMessage}</p>}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="flex flex-col gap-3 rounded-xl border border-border bg-background p-4 lg:col-span-1">
          <span className="text-[10px] font-semibold uppercase tracking-widest text-foreground/40">
            ショップ別クリック数
          </span>
          {clicks ? (
            <>
              <p className="font-display text-2xl font-semibold text-foreground">
                {clicks.total}
                <span className="ml-1 text-xs font-normal text-foreground/40">件（累計）</span>
              </p>
              <ShopBars byShop={clicks.by_shop} />
              {clicks.top_products.length > 0 && (
                <div className="mt-2 border-t border-border pt-2">
                  <span className="text-[10px] font-semibold uppercase tracking-widest text-foreground/40">
                    最高クリック商品
                  </span>
                  <ol className="mt-1.5 flex flex-col gap-1">
                    {clicks.top_products.slice(0, 5).map((p, i) => (
                      <li key={p.product_id} className="flex items-center gap-2 text-xs">
                        <span className="text-foreground/35">{i + 1}.</span>
                        <span className="flex-1 truncate text-foreground/70">{p.product_name}</span>
                        <span className="shrink-0 font-semibold text-foreground">{p.clicks}件</span>
                      </li>
                    ))}
                  </ol>
                </div>
              )}
            </>
          ) : (
            <p className="text-xs text-foreground/40">読み込み中...</p>
          )}
          <div className="mt-2 border-t border-border pt-2">
            <span className="text-[10px] font-semibold uppercase tracking-widest text-foreground/40">
              サイト全体PV（直近28日・上位ページ合計）
            </span>
            {ga4Configured && topPages ? (
              <p className="mt-1 font-display text-lg font-semibold text-foreground">
                {topPages.reduce((sum, p) => sum + p.pageviews, 0).toLocaleString("ja-JP")}
                <span className="ml-1 text-xs font-normal text-foreground/40">PV</span>
              </p>
            ) : (
              <p className="mt-1 text-xs text-foreground/40">GA4未設定のため取得できません</p>
            )}
          </div>
        </div>

        <div className="flex flex-col gap-2 rounded-xl bg-ink p-4 lg:col-span-2">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-signal-high" aria-hidden />
            <span className="text-[10px] font-semibold uppercase tracking-widest text-white/50">
              AI Team Conference
            </span>
          </div>
          <div className="flex max-h-96 flex-col gap-2.5 overflow-y-auto pr-1">
            {messages.length === 0 && <p className="text-xs text-white/40">まだ会話履歴がありません。</p>}
            {messages.map((m) => {
              const persona = PERSONAS.find((p) => p.id === m.persona)!;
              return (
                <div key={m.id} className={`flex gap-2 ${m.fresh ? "animate-fade-up" : ""}`}>
                  <span className="mt-0.5 shrink-0 text-base" aria-hidden>
                    {persona.icon}
                  </span>
                  <div className="min-w-0 flex-1 rounded-xl rounded-tl-sm bg-white/10 px-3 py-2">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-bold uppercase tracking-widest text-brand-light">
                        {persona.role}
                      </span>
                      <span className="text-[10px] text-white/30">{formatTime(m.timestamp)}</span>
                    </div>
                    <p className="mt-0.5 text-xs leading-relaxed text-white/85">{m.text}</p>
                  </div>
                </div>
              );
            })}
            {meetingThinking && (
              <div className="flex gap-2">
                <span className="mt-0.5 shrink-0 text-base" aria-hidden>
                  {PERSONAS.find((p) => p.id === meetingThinking)!.icon}
                </span>
                <div className="rounded-xl rounded-tl-sm bg-white/10 px-3 py-2">
                  <span className="inline-flex gap-1">
                    <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-white/50 [animation-delay:-0.3s]" />
                    <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-white/50 [animation-delay:-0.15s]" />
                    <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-white/50" />
                  </span>
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>
        </div>
      </div>
    </div>
  );
}
