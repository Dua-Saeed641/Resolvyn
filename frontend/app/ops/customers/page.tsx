"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/layout/AppShell";
import { Card, Kv } from "@/components/ui/primitives";
import { StatusBadge } from "@/components/ui/StatusBadge";
import type { CustomerProfile, Ticket } from "@/features/types";
import { api } from "@/lib/api";
import { fmtDateTime } from "@/lib/format";
import { cx } from "@/lib/utils";

/** project.md §17, §69: customer context and history. */
export default function CustomersPage() {
  const [customers, setCustomers] = useState<CustomerProfile[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [detail, setDetail] = useState<(CustomerProfile & { tickets: Ticket[] }) | null>(null);

  useEffect(() => {
    api.get<CustomerProfile[]>("/customers").then((c) => {
      setCustomers(c);
      const want = new URLSearchParams(window.location.search).get("id");
      setSelected(want ?? c[0]?.customer_id ?? null);
    });
  }, []);
  useEffect(() => {
    if (selected) api.get<CustomerProfile & { tickets: Ticket[] }>(`/customers/${selected}`).then(setDetail);
  }, [selected]);

  return (
    <AppShell title="Customers">
      <div className="mx-auto grid max-w-[1400px] gap-5 lg:grid-cols-[340px_minmax(0,1fr)]">
        <Card bodyClass="p-0">
          {customers.map((c) => (
            <button key={c.customer_id} onClick={() => setSelected(c.customer_id)} className={cx("flex w-full items-center justify-between border-b border-border px-4 py-3 text-left last:border-b-0 hover:bg-card-elevated", selected === c.customer_id && "bg-card-elevated")}>
              <span>
                <span className="block text-sm text-text-primary">{c.name}</span>
                <span className="text-xs text-text-muted">{c.customer_id} · {c.plan}</span>
              </span>
              <span className="text-right text-xs text-text-muted">{c.ticket_count ?? 0} tickets{c.open ? ` · ${c.open} open` : ""}</span>
            </button>
          ))}
        </Card>

        {detail && (
          <div className="space-y-5">
            <Card title={detail.name} subtitle={`${detail.customer_id} · ${detail.email ?? ""}`}>
              <dl className="grid gap-x-8 md:grid-cols-2">
                <Kv label="Plan">{detail.plan}</Kv>
                <Kv label="Account age">{detail.account_age_years} year(s)</Kv>
                <Kv label="Previous tickets">{detail.previous_tickets}</Kv>
                <Kv label="Recent sentiment">{detail.recent_sentiment}</Kv>
                <Kv label="Registered phone">••••{detail.phone_last4}</Kv>
                <Kv label="Open issues">{detail.tickets.filter((t) => t.status !== "RESOLVED").length}</Kv>
              </dl>
            </Card>
            <Card title="History" bodyClass="p-0">
              {detail.tickets.length === 0 ? (
                <p className="p-4 text-sm text-text-muted">No tickets for this customer yet.</p>
              ) : (
                detail.tickets.map((t) => (
                  <Link key={t.ticket_id} href={`/ops/tickets/${t.ticket_id}`} className="grid grid-cols-[88px_1fr_140px_130px] items-center gap-3 border-b border-border px-4 py-2.5 text-[13px] last:border-b-0 hover:bg-card-elevated">
                    <span className="font-medium text-text-primary">{t.ticket_id}</span>
                    <span className="min-w-0 truncate text-text-body">{t.subject}</span>
                    <StatusBadge status={t.status} />
                    <span className="text-right text-xs text-text-muted">{fmtDateTime(t.created_at)}</span>
                  </Link>
                ))
              )}
            </Card>
          </div>
        )}
      </div>
    </AppShell>
  );
}
