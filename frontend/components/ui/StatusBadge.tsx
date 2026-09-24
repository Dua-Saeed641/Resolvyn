import { AGENT_STATE_COLOR, STATUS_COLOR, type AgentState, type TicketStatus } from "@/lib/constants";
import { cx } from "@/lib/utils";

/**
 * project.md §57: never rely on color alone — always pair it with a label.
 */
export const TONE_CLASSES = {
  success: "text-success border-success/30 bg-success/10",
  warning: "text-warning border-warning/30 bg-warning/10",
  danger: "text-danger border-danger/30 bg-danger/10",
  info: "text-info border-info/30 bg-info/10",
  muted: "text-text-muted border-border bg-card",
} as const;
export type Tone = keyof typeof TONE_CLASSES;

export function Pill({ tone = "muted", children, className }: { tone?: Tone; children: React.ReactNode; className?: string }) {
  return (
    <span
      className={cx(
        "inline-flex items-center gap-1.5 whitespace-nowrap rounded border px-2 py-0.5 text-xs font-medium",
        TONE_CLASSES[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

const GLYPH: Partial<Record<TicketStatus, string>> = { RESOLVED: "✓", FAILED: "✕", WAITING_FOR_HUMAN: "!" };

export function StatusBadge({ status }: { status: TicketStatus }) {
  const tone = STATUS_COLOR[status] ?? "muted";
  return (
    <Pill tone={tone}>
      {GLYPH[status] ? <span aria-hidden>{GLYPH[status]}</span> : <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden />}
      {status.replaceAll("_", " ")}
    </Pill>
  );
}

export function AgentStateBadge({ state }: { state: AgentState }) {
  return (
    <Pill tone={AGENT_STATE_COLOR[state] ?? "muted"}>
      <span className={cx("h-1.5 w-1.5 rounded-full bg-current", state !== "IDLE" && state !== "COMPLETED" && "animate-pulse")} aria-hidden />
      {state}
    </Pill>
  );
}
