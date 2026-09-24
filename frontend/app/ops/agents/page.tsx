"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/layout/AppShell";
import { Card } from "@/components/ui/primitives";
import { AgentStateBadge, StatusBadge } from "@/components/ui/StatusBadge";
import type { Ticket } from "@/features/types";
import { api } from "@/lib/api";
import { useLive } from "@/lib/live";
import { cx } from "@/lib/utils";

const ROLE: Record<string, string> = {
  Technical: "Errors, diagnostics, product faults",
  Billing: "Payments, refunds, invoices",
  Account: "Login, identity, profile",
  Order: "Orders, shipping, tracking, returns",
  Other: "Anything that fits no specialist desk",
};

/** project.md §19-21, §80: five department agents, deployed on the basis of the caller's query. */
export default function AgentsPage() {
  const { agents, tickets } = useLive();
  const [open, setOpen] = useState<string | null>(null);
  const [list, setList] = useState<Ticket[]>([]);
  useEffect(() => {
    if (!open) return;
    setList(Object.values(tickets).filter((t) => t.assigned_agent === open).sort((a, b) => (a.updated_at < b.updated_at ? 1 : -1)));
  }, [open, tickets]);
  useEffect(() => {
    if (open) api.get<Ticket[]>(`/agents/${open}/tickets`).then(setList).catch(() => undefined);
  }, [open]);

  return (
    <AppShell title="Agents">
      <div className="mx-auto max-w-[1400px] space-y-5">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          {agents.map((a) => (
            <button
              key={a.name}
              onClick={() => setOpen(open === a.name ? null : a.name)}
              aria-pressed={open === a.name}
              className={cx("rounded-lg border bg-card p-4 text-left transition-colors hover:bg-card-elevated", open === a.name ? "border-text-secondary" : "border-border")}
            >
              <div className="flex items-center justify-between">
                <p className="text-sm font-semibold text-text-primary">{a.name} Agent</p>
                <AgentStateBadge state={a.status} />
              </div>
              <p className="mt-1 text-xs text-text-muted">{ROLE[a.name]}</p>
              <dl className="mt-3 space-y-1 text-[13px]">
                <div className="flex justify-between"><dt className="text-text-muted">Current tickets</dt><dd className="tabular-nums text-text-primary">{a.current_tickets ?? 0}</dd></div>
                <div className="flex justify-between"><dt className="text-text-muted">Resolved today</dt><dd className="tabular-nums text-text-primary">{a.resolved_today}</dd></div>
                <div className="flex justify-between"><dt className="text-text-muted">Avg confidence</dt><dd className="tabular-nums text-text-primary">{a.avg_confidence != null ? `${a.avg_confidence}%` : "—"}</dd></div>
              </dl>
              <div className="mt-3 border-t border-border pt-2 text-[11px] text-text-secondary">
                <p>Current task</p>
                <p className="mt-0.5 truncate text-[13px] text-text-body">{a.current_ticket_id ?? "—"}</p>
                <p className="truncate">{a.current_operation ?? "Idle"}</p>
              </div>
            </button>
          ))}
        </div>

        {open && (
          <Card title={`${open} Agent — tickets`} bodyClass="p-0">
            {list.length === 0 ? (
              <p className="p-4 text-sm text-text-muted">No tickets have been routed to this agent yet.</p>
            ) : (
              list.map((t) => (
                <Link key={t.ticket_id} href={`/ops/tickets/${t.ticket_id}`} className="grid grid-cols-[88px_1fr_160px] items-center gap-3 border-b border-border px-4 py-2.5 text-[13px] last:border-b-0 hover:bg-card-elevated">
                  <span className="font-medium text-text-primary">{t.ticket_id}</span>
                  <span className="min-w-0"><span className="block truncate text-text-primary">{t.subject}</span><span className="block truncate text-xs text-text-muted">{t.one_line_summary}</span></span>
                  <StatusBadge status={t.status} />
                </Link>
              ))
            )}
          </Card>
        )}
      </div>
    </AppShell>
  );
}
