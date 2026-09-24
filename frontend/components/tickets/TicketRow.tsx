import Link from "next/link";

import { ConfidenceIndicator } from "@/components/ui/ConfidenceIndicator";
import { PriorityBadge } from "@/components/ui/PriorityBadge";
import { StatusBadge } from "@/components/ui/StatusBadge";
import type { Ticket } from "@/features/tickets/types";
import { timeAgo } from "@/lib/utils";

/** spec §7: Ticket / Customer / Issue / Priority / Intent / Sentiment /
 * Agent / Status / Confidence / Human / Updated — matches TicketTable's
 * column grid exactly. */
export function TicketRow({ ticket, customerName }: { ticket: Ticket; customerName: string }) {
  const needsHuman = ticket.status === "WAITING_FOR_HUMAN";

  return (
    <Link
      href={`/tickets/${ticket.ticket_id}`}
      className="grid grid-cols-[90px_120px_1fr_80px_130px_90px_120px_150px_90px_130px_80px] items-center gap-3 border-b border-border px-4 py-3 text-sm last:border-b-0 hover:bg-card"
    >
      <span className="font-medium text-text-primary">{ticket.ticket_id}</span>
      <span className="truncate text-text-body">{customerName}</span>
      <span className="truncate text-text-body">{ticket.subject}</span>
      <PriorityBadge priority={ticket.priority} />
      <span className="truncate text-text-muted">{ticket.intent ?? "—"}</span>
      <span className="text-text-muted">{ticket.sentiment ?? "—"}</span>
      <span className="truncate text-text-muted">{ticket.assigned_agent ?? "Unassigned"}</span>
      <StatusBadge status={ticket.status} />
      {ticket.confidence !== null ? (
        <ConfidenceIndicator confidence={ticket.confidence} />
      ) : (
        <span className="text-text-muted">—</span>
      )}
      <span className={needsHuman ? "text-warning" : "text-text-muted"}>
        {needsHuman ? "Approval required" : "—"}
      </span>
      <span className="text-text-muted">{timeAgo(ticket.updated_at)}</span>
    </Link>
  );
}
