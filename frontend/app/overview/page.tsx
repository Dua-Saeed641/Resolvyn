import { AppShell } from "@/components/layout/AppShell";
import { EmptyState } from "@/components/ui/EmptyState";
import { MetricCard } from "@/components/ui/MetricCard";
import { TicketRow } from "@/components/tickets/TicketRow";
import type { AnalyticsSummary } from "@/features/analytics/types";
import type { Customer } from "@/features/customers/types";
import type { Ticket } from "@/features/tickets/types";
import { api } from "@/lib/api";

/** project.md §12-13: KPI row + live ticket stream. */
export default async function OverviewPage() {
  let tickets: Ticket[] = [];
  let customers: Customer[] = [];
  let summary: AnalyticsSummary | null = null;
  let backendUnavailable = false;

  try {
    [tickets, customers, summary] = await Promise.all([
      api.get<Ticket[]>("/tickets"),
      api.get<Customer[]>("/customers"),
      api.get<AnalyticsSummary>("/analytics"),
    ]);
  } catch {
    backendUnavailable = true;
  }

  const customerName = (id: string) => customers.find((c) => c.customer_id === id)?.name ?? id;

  return (
    <AppShell title="Overview">
      {backendUnavailable ? (
        <EmptyState
          title="Backend unavailable"
          description="Start the API (see backend/README.md) to see live ticket data."
        />
      ) : (
        <div className="flex flex-col gap-6">
          <div className="grid grid-cols-4 gap-3">
            <MetricCard label="Active tickets" value={summary?.active ?? 0} />
            <MetricCard label="Resolved" value={summary?.resolved ?? 0} />
            <MetricCard label="Human interventions" value={summary?.human_interventions ?? 0} />
            <MetricCard label="Tickets today" value={summary?.tickets_today ?? 0} />
          </div>

          <div>
            <p className="text-sm font-medium text-text-primary">Live tickets</p>
            <p className="text-xs text-text-muted">Real-time support activity</p>
            <div className="mt-3 rounded border border-border">
              {tickets.length === 0 ? (
                <EmptyState
                  title="No active tickets"
                  description="All current conversations have been resolved."
                />
              ) : (
                tickets.map((ticket) => (
                  <TicketRow key={ticket.ticket_id} ticket={ticket} customerName={customerName(ticket.customer_id)} />
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
}
