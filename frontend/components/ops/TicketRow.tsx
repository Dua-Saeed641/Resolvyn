"use client";

import Link from "next/link";

import { AgentBadge, ConfidenceIndicator } from "@/components/ui/primitives";
import { Pill, StatusBadge } from "@/components/ui/StatusBadge";
import type { Ticket } from "@/features/types";
import { timeAgo } from "@/lib/format";

/** project.md §13: Ticket ID · Customer · Issue · Intent · Agent · Status · Confidence · Updated,
 *  plus the AI's live one-line summary (docs/architecture.md §2.5, team side only). */
export function TicketRow({ ticket, now }: { ticket: Ticket; now: number }) {
  return (
    <Link
      href={`/ops/tickets/${ticket.ticket_id}`}
      className="block border-b border-border px-4 py-3 last:border-b-0 hover:bg-card-elevated focus-visible:bg-card-elevated focus-visible:outline-none"
    >
      <div className="grid grid-cols-[80px_minmax(110px,1fr)_minmax(0,2fr)_104px_180px_176px_92px] items-center gap-3 text-[13px]">
        <span className="font-medium text-text-primary">{ticket.ticket_id}</span>
        <span className="truncate text-text-body">{ticket.customer_name ?? "Unidentified caller"}</span>
        <span className="min-w-0">
          <span className="block truncate text-text-primary">{ticket.subject}</span>
          <span className="block truncate text-xs text-text-muted">{ticket.one_line_summary ?? ticket.intent ?? "Waiting for details…"}</span>
        </span>
        <span className="truncate text-text-muted">{ticket.intent ?? "—"}</span>
        <span className="flex flex-wrap items-center gap-1.5">
          <AgentBadge name={ticket.assigned_agent} />
          {ticket.call_active ? <Pill tone="info">● LIVE</Pill> : null}
        </span>
        <span className="flex flex-col items-start gap-1">
          <StatusBadge status={ticket.status} />
          {ticket.is_first_time_bug ? <span className="text-[11px] font-medium text-danger">First-time bug</span> : null}
          {!ticket.is_first_time_bug && ticket.needs_human ? <span className="text-[11px] font-medium text-warning">Needs human</span> : null}
        </span>
        <span className="text-right">
          <ConfidenceIndicator value={ticket.confidence} />
          <span className="block text-[11px] text-text-secondary">{timeAgo(ticket.updated_at, now)}</span>
        </span>
      </div>
    </Link>
  );
}

export function TicketTableHeader() {
  return (
    <div className="grid grid-cols-[80px_minmax(110px,1fr)_minmax(0,2fr)_104px_180px_176px_92px] gap-3 border-b border-border px-4 py-2 text-[11px] uppercase tracking-wide text-text-secondary">
      <span>Ticket</span>
      <span>Customer</span>
      <span>Issue · AI summary</span>
      <span>Intent</span>
      <span>Agent</span>
      <span>Status</span>
      <span className="text-right">Conf.</span>
    </div>
  );
}
