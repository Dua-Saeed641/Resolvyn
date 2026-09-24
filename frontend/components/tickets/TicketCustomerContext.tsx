import Link from "next/link";

import type { Customer } from "@/features/customers/types";
import type { Ticket } from "@/features/tickets/types";

/** spec §15: relevant context only — no giant CRM profile, no demographics. */
export function TicketCustomerContext({
  customer,
  relatedTickets,
  currentTicket,
}: {
  customer: Customer;
  relatedTickets: Ticket[];
  currentTicket: Ticket;
}) {
  const history = relatedTickets.filter((t) => t.ticket_id !== currentTicket.ticket_id);

  return (
    <div className="text-sm">
      <p className="font-medium text-text-primary">{customer.name}</p>
      <dl className="mt-2 grid grid-cols-2 gap-y-1.5 text-xs">
        <dt className="text-text-muted">Customer ID</dt>
        <dd className="text-text-body">{customer.customer_id}</dd>
        <dt className="text-text-muted">Plan</dt>
        <dd className="text-text-body">{customer.plan}</dd>
        {currentTicket.order_id && (
          <>
            <dt className="text-text-muted">Current order</dt>
            <dd className="text-text-body">{currentTicket.order_id}</dd>
          </>
        )}
        <dt className="text-text-muted">Recent sentiment</dt>
        <dd className="text-text-body">{customer.recent_sentiment}</dd>
      </dl>

      <p className="mt-4 text-xs font-medium uppercase tracking-wide text-text-muted">Recent tickets</p>
      {history.length === 0 ? (
        <p className="mt-1 text-xs text-text-muted">No other tickets on file.</p>
      ) : (
        <div className="mt-1.5 flex flex-col gap-1">
          {history.slice(0, 5).map((t) => (
            <Link key={t.ticket_id} href={`/tickets/${t.ticket_id}`} className="text-xs text-text-body hover:text-text-primary">
              <span className="font-medium text-text-primary">{t.ticket_id}</span> — {t.subject}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
