"use client";

import { AgentBadge, ConfidenceIndicator, Kv } from "@/components/ui/primitives";
import { Pill } from "@/components/ui/StatusBadge";
import type { KnowledgeRef, ToolCall, TicketDetail } from "@/features/types";
import { cx } from "@/lib/utils";

const PATH_LABEL: Record<string, string> = {
  INSTANT: "Instant resolve (LLM + memory)",
  ACTION: "Action through tools",
  FIRST_TIME_BUG: "First-time bug",
  ESCALATED: "Escalated to a human",
};

/** project.md §18: Understanding · Agent · Knowledge · Tools. */
export function Understanding({ t }: { t: TicketDetail }) {
  return (
    <dl className="divide-y divide-border/60">
      <Kv label="Intent">{t.intent ?? "—"}</Kv>
      <Kv label="Confidence">
        <ConfidenceIndicator value={t.confidence} />
      </Kv>
      <Kv label="Sentiment">{t.sentiment ?? "—"}</Kv>
      <Kv label="Urgency">{t.urgency ?? "—"}</Kv>
      <Kv label="Priority">
        <span className={cx((t.priority === "HIGH" || t.priority === "CRITICAL") && "text-danger")}>{t.priority}</span>
      </Kv>
      <Kv label="Assigned agent">
        <AgentBadge name={t.assigned_agent} />
      </Kv>
      <Kv label="Resolution path">{t.resolution_path ? PATH_LABEL[t.resolution_path] ?? t.resolution_path : "—"}</Kv>
      <Kv label="Language">{t.language === "hi" ? "Hindi" : "English"}</Kv>
      <Kv label="Channel">{t.channel}</Kv>
      <Kv label="Handled by">{t.handled_by === "HUMAN" ? "Team member" : "AI"}</Kv>
    </dl>
  );
}

export function KnowledgeSources({ sources }: { sources: KnowledgeRef[] }) {
  if (!sources.length) return <p className="text-sm text-text-muted">No knowledge retrieved yet.</p>;
  return (
    <ul className="space-y-1.5">
      {sources.map((s) => (
        <li key={s.chunk_id} className="flex items-center justify-between gap-3 rounded border border-border bg-bg-secondary px-2.5 py-1.5 text-[13px]">
          <span className="min-w-0">
            <span className="block truncate text-text-primary">{s.title}</span>
            <span className="text-[11px] text-text-muted">
              {s.kind.replace("_", " ")} · {s.store === "first_time_bug" ? "first-time-bug memory" : "common memory"} · {s.via === "graph" ? "knowledge graph" : "vector"}
            </span>
          </span>
          <span className="shrink-0 tabular-nums text-xs text-text-body">{s.score.toFixed(2)}</span>
        </li>
      ))}
    </ul>
  );
}

const TOOL_GLYPH: Record<ToolCall["status"], { g: string; cls: string; label: string }> = {
  NOT_STARTED: { g: "○", cls: "text-text-secondary", label: "Not started" },
  WAITING: { g: "→", cls: "text-warning", label: "Waiting" },
  COMPLETED: { g: "✓", cls: "text-success", label: "Completed" },
  FAILED: { g: "✕", cls: "text-danger", label: "Failed" },
};

/** Real tool state only: NOT_STARTED → WAITING → COMPLETED / FAILED (docs/claude.md). Simulated APIs. */
export function ToolCalls({ calls }: { calls: ToolCall[] }) {
  if (!calls.length) return <p className="text-sm text-text-muted">No tools called yet.</p>;
  return (
    <ul className="space-y-1">
      {calls.map((c) => {
        const s = TOOL_GLYPH[c.status];
        return (
          <li key={c.tool_call_id} className="flex items-center justify-between gap-3 text-[13px]">
            <span className="min-w-0 truncate font-mono text-xs text-text-body">
              {c.tool_name}({Object.values(c.request ?? {}).join(", ")})
            </span>
            <span className={cx("shrink-0 text-xs", s.cls)}>
              <span aria-hidden>{s.g}</span> {s.label}
            </span>
          </li>
        );
      })}
      <li className="pt-1">
        <Pill>Simulation · mock enterprise APIs</Pill>
      </li>
    </ul>
  );
}
