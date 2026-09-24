import Link from "next/link";

import { AppShell } from "@/components/layout/AppShell";
import { EmptyState } from "@/components/ui/EmptyState";
import type { ToolCallRecord } from "@/features/tickets/types";
import { api } from "@/lib/api";
import { formatClock } from "@/lib/utils";
import { cx } from "@/lib/utils";

const STATE_MARK: Record<ToolCallRecord["status"], string> = {
  COMPLETED: "✓",
  WAITING: "→",
  NOT_STARTED: "○",
  FAILED: "✗",
};

/** spec §18: tool/API activity across the whole system, not just one ticket. */
export default async function ToolActivityPage() {
  const calls = await api.get<ToolCallRecord[]>("/tool-activity").catch(() => [] as ToolCallRecord[]);

  return (
    <AppShell title="Tool Activity">
      {calls.length === 0 ? (
        <EmptyState title="No tool activity" description="Tool calls will appear here as agents act on tickets." />
      ) : (
        <div className="rounded border border-border">
          {calls.map((c) => (
            <div key={c.tool_call_id} className="flex items-center gap-3 border-b border-border px-4 py-2 text-sm last:border-b-0">
              <span className={cx(c.status === "FAILED" ? "text-danger" : c.status === "COMPLETED" ? "text-success" : "text-text-muted")}>
                {STATE_MARK[c.status]}
              </span>
              <span className="w-56 truncate font-mono text-text-body">{c.tool_name}()</span>
              <Link href={`/tickets/${c.ticket_id}`} className="text-text-primary hover:underline">
                {c.ticket_id}
              </Link>
              <span className="flex-1 truncate text-text-muted">{c.response ?? c.request ?? ""}</span>
              <span className="text-text-muted">{formatClock(c.timestamp)}</span>
            </div>
          ))}
        </div>
      )}
    </AppShell>
  );
}
