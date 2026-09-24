import { TicketRow } from "@/components/tickets/TicketRow";
import { EmptyState } from "@/components/ui/EmptyState";
import type { Customer } from "@/features/customers/types";
import type { Ticket } from "@/features/tickets/types";

const COLUMNS = [
  "Ticket",
  "Customer",
  "Issue",
  "Priority",
  "Intent",
  "Sentiment",
  "Agent",
  "Status",
  "Confidence",
  "Human",
  "Updated",
];

/** spec §7-8: dense operational ticket table — the support team's workspace. */
export function TicketTable({ tickets, customers }: { tickets: Ticket[]; customers: Customer[] }) {
  const customerName = (id: string) => customers.find((c) => c.customer_id === id)?.name ?? id;

  if (tickets.length === 0) {
    return <EmptyState title="No tickets" description="No support tickets match the current filter." />;
  }

  return (
    <div className="overflow-x-auto rounded border border-border">
      <div className="min-w-[980px]">
        <div className="grid grid-cols-[90px_120px_1fr_80px_130px_90px_120px_150px_90px_130px_80px] gap-3 border-b border-border bg-card px-4 py-2 text-[11px] uppercase tracking-wide text-text-muted">
          {COLUMNS.map((c) => (
            <span key={c}>{c}</span>
          ))}
        </div>
        {tickets.map((ticket) => (
          <TicketRow key={ticket.ticket_id} ticket={ticket} customerName={customerName(ticket.customer_id)} />
        ))}
      </div>
    </div>
  );
}
