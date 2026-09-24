import { notFound } from "next/navigation";

import { AppShell } from "@/components/layout/AppShell";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { ConfidenceIndicator } from "@/components/ui/ConfidenceIndicator";
import type { Ticket } from "@/features/tickets/types";
import { api, ApiError } from "@/lib/api";

/** project.md §15: conversation | AI operations, with a timeline below.
 * The full split-panel layout (customer conversation, AI operations panel,
 * event timeline) lands once messages/agent_events are backed by real
 * persistence — see docs/architecture.md §3 mapping table. */
export default async function TicketDetailPage({ params }: { params: { ticketId: string } }) {
  let ticket: Ticket;
  try {
    ticket = await api.get<Ticket>(`/tickets/${params.ticketId}`);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }

  return (
    <AppShell title={ticket.ticket_id}>
      <div className="flex items-center gap-3">
        <StatusBadge status={ticket.status} />
        {ticket.confidence !== null && <ConfidenceIndicator confidence={ticket.confidence} />}
      </div>
      <p className="mt-4 max-w-2xl text-sm text-text-body">{ticket.subject}</p>
      <dl className="mt-6 grid grid-cols-2 gap-y-2 text-xs">
        <dt className="text-text-muted">Intent</dt>
        <dd className="text-text-body">{ticket.intent ?? "—"}</dd>
        <dt className="text-text-muted">Sentiment</dt>
        <dd className="text-text-body">{ticket.sentiment ?? "—"}</dd>
        <dt className="text-text-muted">Assigned agent</dt>
        <dd className="text-text-body">{ticket.assigned_agent ?? "Unassigned"}</dd>
      </dl>
    </AppShell>
  );
}
