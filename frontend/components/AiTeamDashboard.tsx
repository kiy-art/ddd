"use client";

import { useEffect, useRef, useState } from "react";

import { adminFetchRakuten, adminGetLogs, ErrorLog } from "@/lib/api";
import { useLiveJobUpdates, type LiveJobRun, type LiveJobStage } from "@/lib/useLiveJobUpdates";

// Every log line and status shown here comes from a real backend event -
// the same SSE stream (app/progress.py) and ErrorLog rows (app/crud.py's
// create_error_log) that already power 実況ダッシュボード and /admin/logs.
// This component is purely a persona-themed re-skin of that real data: it
// never invents a log line, a metric, or an activity that didn't actually
// happen (this site's standing anti-fabrication rule - see
// docs/ai_company_guidelines.md - applies just as much to an internal
// admin page as to anything shown to a visitor).

type PersonaId = "ceo" | "cmo" | "cro" | "cpo" | "cso";
type Status = "ONLINE" | "ANALYZING" | "DEPLOYING" | "IDLE";

interface Persona {
  id: PersonaId;
  role: string;
  title: string;
  focus: string;
  icon: string;
  // Real backend stage ids (see app/progress.py's STAGE_LABELS) this
  // persona is the "face" of. Empty = CEO, who represents the whole run.
  stages: string[];
}

const PERSONAS: Persona[] = [
  { id: "ceo", role: "CEO AI", title: "Chief Executive Officer", focus: "全体戦略・PDCA統括", icon: "🧭", stages: [] },
  {
    id: "cso",
    role: "CSO AI",
    title: "Chief Strategy Officer",
    focus: "新商品探索・トレンド分析",
    icon: "🔭",
    stages: ["discovery", "popularity"],
  },
  {
    id: "cro",
    role: "CRO AI",
    title: "Chief Revenue Officer",
    focus: "価格データ分析・値下がり通知",
    icon: "📊",
    stages: ["rakuten_prices", "yahoo_prices", "price_alerts"],
  },
  {
    id: "cpo",
    role: "CPO AI",
    title: "Chief Product Officer",
    focus: "買い時判定・データ品質",
    icon: "🛠️",
    stages: ["analysis", "title_cleanup"],
  },
  {
    id: "cmo",
    role: "CMO AI",
    title: "Chief Marketing Officer",
    focus: "SEO・集客・SNS発信",
    icon: "📣",
    stages: ["x_post"],
  },
];

// How long a persona keeps showing "DEPLOYING" after its stage finishes -
// a transition pulse reacting to a real finish_stage event, not a timer
// pretending to be new work.
const DEPLOYING_DURATION_MS = 2500;

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

interface LogLine {
  id: string;
  persona: PersonaId;
  text: string;
  timestamp: number;
  fresh: boolean;
}

function formatTime(ts: number): string {
  return new Date(ts).toLocaleTimeString("ja-JP", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function stageLogText(stage: LiveJobStage, phase: "start" | "done"): string {
  if (phase === "start") return `${stage.label}...`;
  return stage.detail ? `${stage.label} 完了 - ${stage.detail}` : `${stage.label} 完了`;
}

function personaForStage(stageId: string): PersonaId {
  for (const p of PERSONAS) {
    if (p.stages.includes(stageId)) return p.id;
  }
  return "ceo";
}

function useDerivedLog(run: LiveJobRun | null, seed: LogLine[]) {
  const [lines, setLines] = useState<LogLine[]>(seed);
  const seededRef = useRef(false);
  const prevStagesRef = useRef<Map<string, LiveJobStage["status"]>>(new Map());

  useEffect(() => {
    if (!seededRef.current && seed.length > 0) {
      setLines(seed);
      seededRef.current = true;
    }
  }, [seed]);

  useEffect(() => {
    if (!run) return;
    const prev = prevStagesRef.current;
    const next = new Map<string, LiveJobStage["status"]>();
    const additions: LogLine[] = [];

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
          fresh: true,
        });
      } else if (prevStatus === "running" && stage.status === "done") {
        additions.push({
          id: `${run.started_at}-${key}-done`,
          persona: personaForStage(stage.stage),
          text: stageLogText(stage, "done"),
          timestamp: Date.now(),
          fresh: true,
        });
      }
    });

    prevStagesRef.current = next;
    if (additions.length > 0) {
      setLines((current) => [...current.map((l) => ({ ...l, fresh: false })), ...additions].slice(-60));
    }
  }, [run]);

  return lines;
}

function StatusPulse({ status }: { status: Status }) {
  const meta: Record<Status, { color: string; label: string; pulse: boolean }> = {
    ONLINE: { color: "bg-signal-high", label: "ONLINE", pulse: false },
    ANALYZING: { color: "bg-brand", label: "ANALYZING", pulse: true },
    DEPLOYING: { color: "bg-accent-dark", label: "DEPLOYING", pulse: true },
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

function PersonaCard({
  persona,
  status,
  lastLine,
}: {
  persona: Persona;
  status: Status;
  lastLine: LogLine | undefined;
}) {
  return (
    <div
      className={`flex flex-col gap-2.5 rounded-2xl border p-4 transition-colors ${
        status === "ANALYZING" || status === "DEPLOYING" ? "border-brand/40 bg-brand/5" : "border-border bg-card"
      }`}
    >
      <div className="flex items-center justify-between">
        <span className="text-2xl" aria-hidden>
          {persona.icon}
        </span>
        <StatusPulse status={status} />
      </div>
      <div>
        <p className="font-display text-sm font-semibold text-foreground">{persona.role}</p>
        <p className="text-[11px] text-foreground/45">{persona.title}</p>
      </div>
      <p className="text-[11px] leading-relaxed text-foreground/55">{persona.focus}</p>
      <p className="mt-auto truncate border-t border-border pt-2 text-[11px] text-foreground/40">
        {lastLine ? lastLine.text : "実行履歴なし"}
      </p>
    </div>
  );
}

export default function AiTeamDashboard({ token }: { token: string | null }) {
  const { run } = useLiveJobUpdates(token);
  const [seedLines, setSeedLines] = useState<LogLine[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [now, setNow] = useState(() => Date.now());
  const logEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!token) return;
    adminGetLogs(token)
      .then((logs: ErrorLog[]) => {
        const seeded = [...logs]
          .reverse()
          .slice(-20)
          .map((log) => ({
            id: `seed-${log.id}`,
            persona: sourceToPersona(log.source),
            text: log.message,
            timestamp: new Date(log.created_at).getTime(),
            fresh: false,
          }));
        setSeedLines(seeded);
      })
      .catch(() => setSeedLines([]));
  }, [token]);

  const lines = useDerivedLog(run, seedLines);

  // Ticks every 500ms purely so DEPLOYING's 2.5s window (computed from a
  // real finish_stage timestamp) expires back to ONLINE on screen without
  // needing a fresh server event to trigger a re-render.
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 500);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [lines.length]);

  const statusFor = (persona: Persona): Status => {
    const myLines = lines.filter((l) => l.persona === persona.id);
    const runningStageIds = persona.id === "ceo" ? PERSONAS.flatMap((p) => p.stages) : persona.stages;
    const isRunning =
      !!run &&
      run.status === "running" &&
      (persona.id === "ceo" ? true : run.stage !== null && runningStageIds.includes(run.stage));
    if (isRunning) return "ANALYZING";

    const lastFinished = [...myLines].reverse().find((l) => l.text.includes("完了"));
    if (lastFinished && now - lastFinished.timestamp < DEPLOYING_DURATION_MS) return "DEPLOYING";

    if (myLines.length === 0 && !run) return "IDLE";
    return "ONLINE";
  };

  const handleRunAll = async () => {
    if (!token) return;
    const confirmed = window.confirm(
      "本番の日次バッチ処理（楽天/Yahoo価格取得・新商品探索・買い時再判定・値下がり通知・SNS投稿）を今すぐ実行します。" +
        "「今すぐ価格を取得」ボタンと全く同じ処理で、外部APIへの実際のリクエストが発生します。\n\n実行しますか？"
    );
    if (!confirmed) return;
    setBusy(true);
    setMessage(null);
    try {
      const result = await adminFetchRakuten(token);
      setMessage(
        `全AIロールのPDCAサイクル完了: 価格更新${result.prices_updated}件 / 新商品${result.products_discovered}件 / AI再生成${result.ai_regenerated}件`
      );
    } catch (err) {
      setMessage(`実行失敗: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-border bg-card p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="font-display font-medium text-foreground">AI Team Operations</h2>
          <p className="text-xs text-foreground/45">
            実際の日次バッチ処理（楽天/Yahoo価格取得・新商品探索・買い時判定・通知）を5つの役割に分けて表示しています。
          </p>
        </div>
        <button
          type="button"
          onClick={handleRunAll}
          disabled={busy || !token}
          className="shrink-0 rounded-full bg-brand px-5 py-2.5 text-xs font-semibold text-white disabled:opacity-50"
        >
          {busy ? "実行中..." : "全AIのPDCAサイクルを実行"}
        </button>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {PERSONAS.map((persona) => {
          const myLines = lines.filter((l) => l.persona === persona.id);
          return (
            <PersonaCard
              key={persona.id}
              persona={persona}
              status={statusFor(persona)}
              lastLine={myLines[myLines.length - 1]}
            />
          );
        })}
      </div>

      {message && <p className="text-xs text-foreground/60">{message}</p>}

      <div className="rounded-xl bg-ink p-4">
        <div className="mb-2 flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-signal-high" aria-hidden />
          <span className="text-[10px] font-semibold uppercase tracking-widest text-white/50">
            AI Agent Stream
          </span>
        </div>
        <div className="flex max-h-64 flex-col gap-1 overflow-y-auto font-mono text-[11px] leading-relaxed">
          {lines.length === 0 && <p className="text-white/40">まだ実行履歴がありません。</p>}
          {lines.map((line) => {
            const persona = PERSONAS.find((p) => p.id === line.persona)!;
            return (
              <p
                key={line.id}
                className={`text-white/80 ${line.fresh ? "animate-fade-up" : ""}`}
              >
                <span className="text-white/35">[{formatTime(line.timestamp)}]</span>{" "}
                <span className="text-brand-light">[{persona.role}]</span> {line.text}
              </p>
            );
          })}
          <div ref={logEndRef} />
        </div>
      </div>
    </div>
  );
}
