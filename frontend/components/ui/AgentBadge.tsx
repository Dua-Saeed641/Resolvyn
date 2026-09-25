import type { AgentState } from "@/lib/constants";
import { cx } from "@/lib/utils";

const ACTIVE_STATES: AgentState[] = ["ANALYZING", "RETRIEVING", "ACTING", "VERIFYING"];

export function AgentBadge({ name, status }: { name: string; status: AgentState }) {
  const isActive = ACTIVE_STATES.includes(status) || status === "COMPLETED";
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-text-body">
      <span
        className={cx(
          "h-1.5 w-1.5 rounded-full",
          status === "ERROR" ? "bg-danger" : isActive ? "bg-success" : "bg-text-muted"
        )}
        aria-hidden
      />
      {name}
      <span className="text-text-muted">{status}</span>
    </span>
  );
}
