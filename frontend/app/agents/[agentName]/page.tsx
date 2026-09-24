import { notFound } from "next/navigation";

import { AppShell } from "@/components/layout/AppShell";
import { AgentBadge } from "@/components/ui/AgentBadge";
import { TicketTable } from "@/components/tickets/TicketTable";
import type { Agent } from "@/features/agents/types";
import type { Customer } from "@/features/customers/types";
import type { Ticket, TicketEvent } from "@/features/tickets/types";
import { ActivityEvent } from "@/components/activity/ActivityEvent";
import { EmptyState } from "@/components/ui/EmptyState";
import { api, ApiError } from "@/lib/api";
import { formatClock } from "@/lib/utils";

/** spec §21: current ticket, current operation, recent tickets, recent
 * tool/human activity — enough to understand the agent without reading code. */
export default async function AgentDetailPage({ params }: { params: { agentName: string } }) {
  const agentName = decodeURIComponent(params.agentName);

  let agent: Agent;
  try {
    agent = await api.get<Agent>(`/agents/${encodeURIComponent(agentName)}`);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }

  const [tickets, customers, events] = await Promise.all([
    api.get<Ticket[]>("/tickets"),
    api.get<Customer[]>("/customers"),
    api.get<TicketEvent[]>(`/agents/${encodeURIComponent(agentName)}/events`),
  ]);

  const handled = tickets.filter((t) => t.assigned_agent === agentName);

  return (
    <AppShell title={agentName}>
      <div className="flex flex-col gap-6">
        <div className="rounded border border-border bg-card p-4">
          <AgentBadge name={agent.name} status={agent.status} />
          <p className="mt-2 text-xs text-text-muted">
            {agent.current_ticket_id ? `Current ticket: ${agent.current_ticket_id}` : "No active ticket"}
          </p>
        </div>

        <div>
          <p className="mb-2 text-sm font-medium text-text-primary">Tickets handled</p>
          <TicketTable tickets={handled} customers={customers} />
        </div>

        <div>
          <p className="mb-2 text-sm font-medium text-text-primary">Recent activity</p>
          <div className="rounded border border-border">
            {events.length === 0 ? (
              <EmptyState title="No recent activity" description="This agent has no recorded events yet." />
            ) : (
              events.map((e) => (
                <ActivityEvent key={e.event_id} timestamp={formatClock(e.timestamp)} description={`${e.ticket_id} — ${e.description ?? e.event_type}`} />
              ))
            )}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
