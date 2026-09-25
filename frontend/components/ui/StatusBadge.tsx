import { Badge } from "@/components/ui/badge";
import { AGENT_STATE_COLOR, STATUS_COLOR, type AgentState, type TicketStatus } from "@/lib/constants";
import { cx } from "@/lib/utils";

/** Never rely on colour alone: every status pairs its colour with a label and a marker. */
export const TONE_CLASSES = {
  success: "text-success border-success/25 bg-success/10",
  warning: "text-warning border-warning/30 bg-warning/10",
  danger: "text-danger border-danger/25 bg-danger/10",
  info: "text-info border-info/25 bg-info/10",
  muted: "text-muted-foreground border-border bg-muted/60",
} as const;
export type Tone = keyof typeof TONE_CLASSES;

export function Pill({ tone = "muted", children, className }: { tone?: Tone; children: React.ReactNode; className?: string }) {
  return (
    <Badge variant={tone} className={className}>
      {children}
    </Badge>
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
