import Link from "next/link";

import { ConfidenceIndicator } from "@/components/ui/ConfidenceIndicator";
import { StatusBadge } from "@/components/ui/StatusBadge";
import type { Ticket } from "@/features/tickets/types";

/** project.md §13: Ticket ID, Customer, Issue, Intent, Agent, Status, Confidence, Updated. */
export function TicketRow({ ticket, customerName }: { ticket: Ticket; customerName: string }) {
  return (
    <Link
      href={`/tickets/${ticket.ticket_id}`}
      className="grid grid-cols-[100px_140px_1fr_120px_140px_140px_100px] items-center gap-3 border-b border-border px-4 py-3 text-sm hover:bg-card"
    >
      <span className="font-medium text-text-primary">{ticket.ticket_id}</span>
      <span className="text-text-body">{customerName}</span>
      <span className="truncate text-text-body">{ticket.subject}</span>
      <span className="text-text-muted">{ticket.intent ?? "—"}</span>
      <span className="text-text-muted">{ticket.assigned_agent ?? "Unassigned"}</span>
      <StatusBadge status={ticket.status} />
      {ticket.confidence !== null ? (
        <ConfidenceIndicator confidence={ticket.confidence} />
      ) : (
        <span className="text-text-muted">—</span>
      )}
    </Link>
  );
}
