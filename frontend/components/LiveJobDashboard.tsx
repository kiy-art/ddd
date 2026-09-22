"use client";

import { useLiveJobUpdates, type LiveJobStage } from "@/lib/useLiveJobUpdates";

const STAGE_ICONS: Record<string, string> = {
  rakuten_prices: "💰",
  yahoo_prices: "💰",
  discovery: "🔍",
  popularity: "📈",
  analysis: "🤖",
  price_alerts: "📧",
  x_post: "📣",
};

function StageRow({ stage }: { stage: LiveJobStage }) {
  const running = stage.status === "running";
  const hasProgress = stage.current !== null && stage.total !== null && stage.total > 0;
  const percent = hasProgress ? Math.min(100, Math.round((stage.current! / stage.total!) * 100)) : null;

  return (
    <div
      className={`flex flex-col gap-1.5 rounded-xl border px-4 py-3 transition-colors ${
        running ? "border-brand bg-brand/5" : "border-border bg-background"
      }`}
    >
      <div className="flex items-center gap-2">
        <span
          className={`flex h-2.5 w-2.5 shrink-0 rounded-full ${
            running ? "animate-pulse bg-brand" : "bg-signal-high"
          }`}
          aria-hidden
        />
        <span className="text-base leading-none" aria-hidden>
          {STAGE_ICONS[stage.stage] ?? "⚙️"}
        </span>
        <span className={`text-sm font-medium ${running ? "text-brand" : "text-foreground"}`}>
          {stage.label}
        </span>
        {hasProgress && (
          <span className="ml-auto text-xs tabular-nums text-foreground/50">
            {stage.current} / {stage.total}
          </span>
        )}
      </div>
      {hasProgress && (
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-border">
          <div
            className={`h-full rounded-full transition-[width] duration-300 ${
              running ? "bg-brand" : "bg-signal-high"
            }`}
            style={{ width: `${percent}%` }}
          />
        </div>
      )}
      {stage.detail && <p className="text-xs text-foreground/50">{stage.detail}</p>}
    </div>
  );
}

export default function LiveJobDashboard({ token }: { token: string | null }) {
  const { run, connected } = useLiveJobUpdates(token);

  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-border bg-card p-5">
      <div className="flex items-center justify-between">
        <h2 className="font-display font-medium text-foreground">実況ダッシュボード</h2>
        <span
          className={`flex items-center gap-1.5 text-xs ${connected ? "text-foreground/50" : "text-sale"}`}
        >
          <span
            className={`h-1.5 w-1.5 rounded-full ${connected ? "bg-signal-high" : "bg-sale"}`}
            aria-hidden
          />
          {connected ? "接続中" : "再接続中…"}
        </span>
      </div>

      {!run && <p className="text-sm text-foreground/50">実行中のジョブはありません。下のボタンから実行すると、ここに進行状況が表示されます。</p>}

      {run && (
        <div className="flex flex-col gap-3">
          <div className="flex items-center gap-2">
            <span
              className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                run.status === "running" ? "bg-brand text-white" : "bg-signal-high/20 text-signal-high"
              }`}
            >
              {run.status === "running" ? "実行中" : "完了"}
            </span>
            <span className="text-sm font-medium text-foreground">{run.job_label}</span>
          </div>
          <div className="flex flex-col gap-2">
            {run.stages.map((stage, i) => (
              <StageRow key={`${stage.stage}-${i}`} stage={stage} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
