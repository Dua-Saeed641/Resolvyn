import Link from "next/link";

import { AppShell } from "@/components/layout/AppShell";
import { TicketTable } from "@/components/tickets/TicketTable";
import type { Customer } from "@/features/customers/types";
import type { Ticket } from "@/features/tickets/types";
import { api } from "@/lib/api";
import { cx } from "@/lib/utils";

const TABS = [
  { label: "All", value: "all", status: undefined },
  { label: "Active", value: "active", status: "ACTIVE" },
  { label: "Waiting for Human", value: "waiting", status: "WAITING_FOR_HUMAN" },
  { label: "Resolved", value: "resolved", status: "RESOLVED" },
] as const;

/** spec §8: the internal support team's ticket workspace, not a customer list. */
export default async function TicketsPage({
  searchParams,
}: {
  searchParams: { tab?: string };
}) {
  const activeTab = TABS.find((t) => t.value === searchParams.tab) ?? TABS[0];

  const [tickets, customers] = await Promise.all([
    api.get<Ticket[]>(activeTab.status ? `/tickets?status=${activeTab.status}` : "/tickets").catch(() => [] as Ticket[]),
    api.get<Customer[]>("/customers").catch(() => [] as Customer[]),
  ]);

  return (
    <AppShell title="Tickets">
      <div className="mb-4 flex gap-1 border-b border-border">
        {TABS.map((tab) => (
          <Link
            key={tab.value}
            href={`/tickets?tab=${tab.value}`}
            className={cx(
              "border-b-2 px-3 py-2 text-sm",
              activeTab.value === tab.value
                ? "border-text-primary text-text-primary"
                : "border-transparent text-text-muted hover:text-text-body"
            )}
          >
            {tab.label}
          </Link>
        ))}
      </div>
      <TicketTable tickets={tickets} customers={customers} />
    </AppShell>
  );
}
