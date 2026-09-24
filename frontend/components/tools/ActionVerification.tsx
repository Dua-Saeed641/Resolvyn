import type { ToolCallRecord } from "@/features/tickets/types";
import { cx } from "@/lib/utils";

/** spec §19: ACTION TAKEN must be visually distinct from ACTION VERIFIED —
 * the customer response must never claim success before verification. */
export function ActionVerification({ toolCalls }: { toolCalls: ToolCallRecord[] }) {
  const primary = toolCalls.find((t) => t.tool_name.startsWith("issue_") || t.tool_name.startsWith("reset_"));
  const verification = toolCalls.find((t) => t.tool_name.startsWith("verify_"));

  if (!primary) return null;

  return (
    <div className="rounded border border-border bg-card p-4 text-sm">
      <p className="text-xs font-medium uppercase tracking-wide text-text-muted">Action verification</p>
      <p className="mt-2 text-text-primary">{primary.tool_name.replaceAll("_", " ")}</p>
      <dl className="mt-3 grid grid-cols-2 gap-y-2 text-xs">
        <dt className="text-text-muted">Action taken</dt>
        <dd
          className={cx(
            "font-medium",
            primary.status === "COMPLETED" ? "text-text-primary" : primary.status === "FAILED" ? "text-danger" : "text-warning"
          )}
        >
          {primary.status}
        </dd>
        <dt className="text-text-muted">Action verified</dt>
        <dd className={cx("font-medium", verification?.status === "COMPLETED" ? "text-success" : "text-text-muted")}>
          {verification?.status === "COMPLETED" ? "VERIFIED" : verification ? verification.status : "NOT YET"}
        </dd>
      </dl>
      {primary.response && <p className="mt-3 text-xs text-text-muted">{primary.response}</p>}
    </div>
  );
}
