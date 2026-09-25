"use client";

import Link from "next/link";
import { useState } from "react";

import { AgentBadge, Button, ConfidenceIndicator } from "@/components/ui/primitives";
import { Pill, StatusBadge } from "@/components/ui/StatusBadge";
import type { PendingAction, Ticket } from "@/features/types";
import { api } from "@/lib/api";
import { timeAgo } from "@/lib/format";

const URGENCY_DOT: Record<string, string> = {
  CRITICAL: "bg-danger",
  HIGH: "bg-warning",
  MEDIUM: "bg-info",
  LOW: "bg-text-secondary",
};

/** One ticket, triage-card style: everything a support agent needs to decide
 *  "open it, or act right now" without leaving the queue (project.md §13's
 *  same fields as the table row — ticket · customer · issue · agent · status ·
 *  confidence — laid out as a card instead of a row). Approve/Reject are real
 *  actions (same endpoints as ApprovalCard); there is no decorative button. */
export function TicketCard({ ticket, now, pending }: { ticket: Ticket; now: number; pending: PendingAction | null }) {
  const [busy, setBusy] = useState<"approve" | "reject" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const decide = async (kind: "approve" | "reject") => {
    if (!pending) return;
    setBusy(kind);
    setError(null);
    try {
      await api.post(`/human-intelligence/${kind}`, {
        ticket_id: ticket.ticket_id,
        action_id: pending.action_id,
        reason: kind === "approve" ? "Duplicate transaction verified" : "Rejected by operator",
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Action failed");
    } finally {
      setBusy(null);
    }
  };

  return (
    <article className="animate-fade-in flex flex-col rounded-lg border border-border bg-card p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2">
          <span className={`h-2 w-2 shrink-0 rounded-full ${URGENCY_DOT[ticket.priority] ?? "bg-text-secondary"}`} aria-hidden />
          <Link href={`/ops/tickets/${ticket.ticket_id}`} className="truncate text-sm font-semibold text-text-primary hover:underline">
            {ticket.ticket_id}
          </Link>
          {ticket.call_active && <Pill tone="info">● LIVE</Pill>}
        </div>
        <StatusBadge status={ticket.status} />
      </div>

      <div className="mt-2 flex flex-wrap items-center gap-1.5 text-[13px]">
        <span className="text-text-body">{ticket.customer_name ?? "Unidentified caller"}</span>
        <span className="text-text-secondary">·</span>
        <AgentBadge name={ticket.assigned_agent} />
        {ticket.is_first_time_bug && <Pill tone="danger">First-time bug</Pill>}
        {!ticket.is_first_time_bug && ticket.needs_human && <Pill tone="warning">Needs review</Pill>}
      </div>

      <p className="mt-1.5 line-clamp-2 text-[13px] text-text-body">{ticket.one_line_summary ?? ticket.subject}</p>

      <div className="mt-3 space-y-1.5 border-t border-border pt-3 text-[13px]">
        <div className="flex items-center justify-between gap-3">
          <span className="text-text-muted">AI Confidence</span>
          <ConfidenceIndicator value={ticket.confidence} />
        </div>
        <div className="flex items-start justify-between gap-3">
          <span className="shrink-0 text-text-muted">Suggested action</span>
          <span className="truncate text-right text-text-primary">{ticket.next_step ?? "—"}</span>
        </div>
      </div>

      {error && <p className="mt-2 text-xs text-danger">{error}</p>}

      <div className="mt-3 flex items-center justify-between gap-2 border-t border-border pt-3">
        <div className="flex gap-2">
          {pending && (
            <>
              <Button variant="primary" size="sm" disabled={busy !== null} onClick={() => decide("approve")}>
                {busy === "approve" ? "Approving…" : "Approve"}
              </Button>
              <Button variant="danger" size="sm" disabled={busy !== null} onClick={() => decide("reject")}>
                Reject
              </Button>
            </>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[11px] text-text-secondary">{timeAgo(ticket.updated_at, now)}</span>
          <Link href={`/ops/tickets/${ticket.ticket_id}`}>
            <Button variant="secondary" size="sm">
              Open →
            </Button>
          </Link>
        </div>
      </div>
    </article>
  );
}
