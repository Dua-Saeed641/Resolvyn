"use client";

import { useLive } from "@/lib/live";

/** project.md §11: page title left, system status right. */
export function TopBar({ title }: { title: string }) {
  const { connected, llm, stats } = useLive();
  const model = llm?.live_ready ? "Model ready" : llm ? "Model loading" : null;
  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-border px-6">
      <p className="text-sm font-medium text-text-primary">{title}</p>
      <div className="flex items-center gap-5 text-xs text-text-muted">
        {stats ? (
          <span>
            {stats.live_calls} live call{stats.live_calls === 1 ? "" : "s"}
          </span>
        ) : null}
        {model ? (
          <span className="flex items-center gap-1.5" title="Qwen through the epsilon engine">
            <span className={`h-1.5 w-1.5 rounded-full ${llm?.live_ready ? "bg-success" : "bg-warning"}`} aria-hidden />
            {model}
          </span>
        ) : null}
        <span className="flex items-center gap-1.5">
          <span className={`h-1.5 w-1.5 rounded-full ${connected ? "bg-success" : "bg-danger"}`} aria-hidden />
          {connected ? "Operational" : "Reconnecting…"}
        </span>
      </div>
    </header>
  );
}

