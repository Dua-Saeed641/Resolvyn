import { AppShell } from "@/components/layout/AppShell";
import { TicketRow } from "@/components/tickets/TicketRow";
import { EmptyState } from "@/components/ui/EmptyState";
import type { Customer } from "@/features/customers/types";
import type { Ticket } from "@/features/tickets/types";
import { api } from "@/lib/api";

/** project.md §32: filters (All/Active/Waiting/Resolved/Needs Human/High Risk)
 * are not yet wired up — this renders the unfiltered list until ticket
 * persistence (backend/app/services/ticket_service.py) replaces seed data. */
export default async function TicketsPage() {
  const [tickets, customers] = await Promise.all([
    api.get<Ticket[]>("/tickets").catch(() => [] as Ticket[]),
    api.get<Customer[]>("/customers").catch(() => [] as Customer[]),
  ]);
  const customerName = (id: string) => customers.find((c) => c.customer_id === id)?.name ?? id;

  return (
    <AppShell title="Tickets">
      <div className="rounded border border-border">
        {tickets.length === 0 ? (
          <EmptyState title="No tickets" description="No support tickets are currently on file." />
        ) : (
          tickets.map((ticket) => (
            <TicketRow key={ticket.ticket_id} ticket={ticket} customerName={customerName(ticket.customer_id)} />
          ))
        )}
      </div>
    </AppShell>
  );
}
