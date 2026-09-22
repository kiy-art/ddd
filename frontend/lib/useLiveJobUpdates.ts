"use client";

import { useEffect, useRef, useState } from "react";

import { API_URL, adminHeaders } from "@/lib/api";

export interface LiveJobStage {
  stage: string;
  label: string;
  status: "running" | "done";
  current: number | null;
  total: number | null;
  detail: string | null;
}

export interface LiveJobRun {
  type: string;
  job: string;
  job_label: string;
  status: "running" | "completed";
  stage: string | null;
  stage_label: string | null;
  stages: LiveJobStage[];
  started_at: number;
  finished_at: number | null;
}

// Native EventSource can't send the Authorization header this admin API
// requires (and this project uses a Bearer token, not cookies - see
// app/auth.py), so the SSE stream is read by hand with fetch() +
// ReadableStream instead. Reconnects with a short fixed delay if the
// stream ends or errors (a Render free-tier cold start, a network blip),
// since a live dashboard that silently stops updating is worse than one
// that's briefly unavailable.
const RECONNECT_DELAY_MS = 3000;

export function useLiveJobUpdates(token: string | null) {
  const [run, setRun] = useState<LiveJobRun | null>(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    if (!token) return;
    const controller = new AbortController();
    let stopped = false;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

    async function connect() {
      while (!stopped) {
        try {
          const res = await fetch(`${API_URL}/api/admin/live`, {
            headers: adminHeaders(token as string),
            signal: controller.signal,
            cache: "no-store",
          });
          if (!res.ok || !res.body) {
            throw new Error(`live stream failed: ${res.status}`);
          }
          setConnected(true);

          const reader = res.body.getReader();
          const decoder = new TextDecoder();
          let buffer = "";
          while (!stopped) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const frames = buffer.split("\n\n");
            buffer = frames.pop() ?? "";
            for (const frame of frames) {
              const line = frame.split("\n").find((l) => l.startsWith("data: "));
              if (!line) continue; // e.g. a ": keepalive" comment line
              try {
                setRun(JSON.parse(line.slice("data: ".length)));
              } catch {
                // malformed frame - skip rather than crash the dashboard
              }
            }
          }
        } catch {
          // network error, abort, or the stream simply ended - fall
          // through to the reconnect wait below unless we're stopping
        }
        setConnected(false);
        if (stopped) break;
        await new Promise<void>((resolve) => {
          reconnectTimer = setTimeout(resolve, RECONNECT_DELAY_MS);
        });
      }
    }

    connect();

    return () => {
      stopped = true;
      controller.abort();
      if (reconnectTimer) clearTimeout(reconnectTimer);
    };
  }, [token]);

  return { run, connected };
}
