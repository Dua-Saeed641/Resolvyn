"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { CallPanel } from "@/components/customer/CallPanel";
import { TicketPanel } from "@/components/customer/TicketPanel";
import { StatusBadge } from "@/components/ui/StatusBadge";
import type { CustomerProfile, CustomerTicketView } from "@/features/types";
import { api } from "@/lib/api";
import { fmtDateTime } from "@/lib/format";
import { useCall } from "@/lib/useCall";

/** Customer side: call or chat with the agent, and watch the ticket update in real time. */
export default function CustomerPage() {
  const call = useCall();
  const [customers, setCustomers] = useState<CustomerProfile[]>([]);
  const [customerId, setCustomerId] = useState("");
  const [history, setHistory] = useState<CustomerTicketView[]>([]);

  useEffect(() => {
    api.get<CustomerProfile[]>("/customers").then((c) => {
      setCustomers(c);
      setCustomerId((cur) => cur || c[0]?.customer_id || "");
    }).catch(() => undefined);
  }, []);

  const loadHistory = useCallback(() => {
    if (!customerId) return setHistory([]);
    api.get<CustomerTicketView[]>(`/customers/${customerId}/portal-tickets`).then(setHistory).catch(() => undefined);
  }, [customerId]);
  useEffect(() => {
    loadHistory();
    const t = setInterval(loadHistory, 6000);
    return () => clearInterval(t);
  }, [loadHistory]);

  const currentId = call.ticket?.ticket_id;

  return (
    <div className="min-h-screen bg-bg-primary">
      <header className="flex h-14 items-center justify-between border-b border-border px-6">
        <div className="flex items-baseline gap-3">
          <p className="text-sm font-semibold tracking-[0.18em] text-text-primary">RESOLVYN</p>
          <p className="hidden text-xs text-text-secondary sm:block">Customer support · Nova Retail</p>
        </div>
        <Link href="/ops" className="rounded border border-border px-3 py-1.5 text-xs text-text-muted hover:bg-card hover:text-text-primary">
          Team console →
        </Link>
      </header>

      <main className="mx-auto grid max-w-[1180px] gap-6 px-4 py-6 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)]">
        <div>
          <h1 className="mb-1 text-xl font-semibold text-text-primary">How can we help?</h1>
          <p className="mb-4 max-w-lg text-sm text-text-muted">
            Talk to Riya, or chat with her. She can look at your orders and payments, fix what she can on the spot, and bring in a teammate the moment she needs one.
          </p>
          <CallPanel
            customers={customers}
            status={call.status}
            agentStatus={call.agentStatus}
            lines={call.lines}
            interim={call.interim}
            error={call.error}
            muted={call.muted}
            sttSupported={call.sttSupported}
            ttsFallback={call.ttsFallback}
            sttMode={call.sttMode}
            customerId={customerId}
            onCustomer={setCustomerId}
            onStart={call.start}
            onSend={call.sendText}
            onEnd={call.end}
            onMute={call.toggleMute}
            onReset={call.reset}
            agentName="Riya"
          />
        </div>

        <div className="space-y-6">
          {call.ticket ? (
            <TicketPanel ticket={call.ticket} />
          ) : (
            <section className="rounded-lg border border-dashed border-border bg-card p-6 text-center">
              <p className="text-sm font-medium text-text-primary">Your ticket appears here</p>
              <p className="mx-auto mt-1 max-w-sm text-sm text-text-muted">A ticket is created the moment the call starts and its status updates live while you talk.</p>
            </section>
          )}

          <section aria-label="Your tickets">
            <h2 className="mb-2 text-[13px] font-semibold text-text-primary">Your tickets</h2>
            {history.length === 0 ? (
              <p className="rounded-lg border border-dashed border-border bg-card p-4 text-sm text-text-muted">No tickets yet.</p>
            ) : (
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                {history.slice(0, 8).map((t) => {
                  const latest = t.timeline[t.timeline.length - 1];
                  return (
                    <article
                      key={t.ticket_id}
                      className={`rounded-lg border p-3.5 text-[13px] ${t.ticket_id === currentId ? "border-text-secondary bg-card-elevated" : "border-border bg-card"}`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-medium text-text-primary">{t.ticket_id}</span>
                        <StatusBadge status={t.status} />
                      </div>
                      <p className="mt-1 truncate text-text-body">{t.subject}</p>
                      <p className="mt-1 truncate text-xs text-text-muted">{latest?.text ?? t.status_label}</p>
                      <p className="mt-2 text-[11px] text-text-secondary">{fmtDateTime(t.updated_at)}</p>
                    </article>
                  );
                })}
              </div>
            )}
          </section>
        </div>
      </main>
    </div>
  );
}
