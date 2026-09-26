"use client";

import { useCallback, useEffect, useState } from "react";

import Link from "next/link";

import { Logo, LogoMark } from "@/components/brand/Logo";
import { CallPanel } from "@/components/customer/CallPanel";
import { EmailPanel } from "@/components/customer/EmailPanel";
import { TicketPanel } from "@/components/customer/TicketPanel";
import { ThemeToggle } from "@/components/theme/ThemeToggle";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/StatusBadge";
import type { CustomerProfile, CustomerTicketView } from "@/features/types";
import { api } from "@/lib/api";
import { fmtDateTime } from "@/lib/format";
import { useCall } from "@/lib/useCall";
import { cn } from "@/lib/utils";

/** Talk to Riya, chat with her, or email, and watch the ticket update in real time. Lives on its own page; the home page is the pitch. */
export default function TalkPage() {
  const call = useCall();
  const [customers, setCustomers] = useState<CustomerProfile[]>([]);
  const [customerId, setCustomerId] = useState("");
  const [history, setHistory] = useState<CustomerTicketView[]>([]);

  useEffect(() => {
    api
      .get<CustomerProfile[]>("/customers")
      .then((c) => {
        setCustomers(c);
        setCustomerId((cur) => cur || c[0]?.customer_id || "");
      })
      .catch(() => undefined);
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
  const me = customers.find((c) => c.customer_id === customerId);

  return (
    <div className="min-h-screen bg-background">
      <header className="mx-auto flex h-16 max-w-[1240px] items-center justify-between px-6">
        <Link href="/" aria-label="Resolvyn home">
          <Logo size={34} />
        </Link>
        <div className="flex items-center gap-2">
          <Button asChild variant="ghost" size="sm" className="rounded-full">
            <Link href="/#benchmarks">Benchmarks</Link>
          </Button>
          <Button asChild variant="outline" size="sm" className="rounded-full">
            <Link href="/ops">Team console</Link>
          </Button>
          <ThemeToggle />
        </div>
      </header>

      <section id="talk" className="relative">
        <div className="mx-auto max-w-[1240px] px-6 pb-16 pt-8">
          <div className="mb-10 max-w-2xl">
            <p className="text-sm font-medium text-success">Nova Retail support</p>
            <h2 className="mt-3 font-display text-3xl font-normal tracking-tight sm:text-5xl">Start a conversation.</h2>
            <p className="mt-3 text-muted-foreground">Talk to Riya, chat with her, or send an email. She can look at your orders and payments and sort most things out straight away.</p>
          </div>

          <div className="grid gap-6 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)]">
            <div className="space-y-6">
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
              <EmailPanel customer={me} />
            </div>

            <div className="space-y-6">
              {call.ticket ? (
                <TicketPanel ticket={call.ticket} />
              ) : (
                <Card className="border-dashed p-8 text-center shadow-none">
                  <p className="font-display text-lg">Your ticket appears here</p>
                  <p className="mx-auto mt-1 max-w-sm text-sm text-muted-foreground">A ticket is created the moment you start, and its status updates live while you talk.</p>
                </Card>
              )}

              <section aria-label="Your tickets">
                <h2 className="mb-3 font-display text-lg">{me ? `${me.name.split(" ")[0]}'s tickets` : "Your tickets"}</h2>
                {history.length === 0 ? (
                  <Card className="border-dashed p-5 text-sm text-muted-foreground shadow-none">No tickets yet.</Card>
                ) : (
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                    {history.slice(0, 8).map((t) => {
                      const latest = t.timeline[t.timeline.length - 1];
                      return (
                        <article key={t.ticket_id} className={cn("rounded-xl border bg-card p-4 text-[13px] transition-shadow hover:shadow-float", t.ticket_id === currentId && "ring-2 ring-brand/40")}>
                          <div className="flex items-center justify-between gap-2">
                            <span className="font-display text-sm">{t.ticket_id}</span>
                            <StatusBadge status={t.status} />
                          </div>
                          <p className="mt-2 truncate font-medium">{t.subject}</p>
                          <p className="mt-1 truncate text-xs text-muted-foreground">{latest?.text ?? t.status_label}</p>
                          <p className="mt-3 text-[11px] text-text-secondary">{fmtDateTime(t.updated_at)}</p>
                        </article>
                      );
                    })}
                  </div>
                )}
              </section>
            </div>
          </div>
        </div>
      </section>

      <footer className="border-t">
        <div className="mx-auto flex max-w-[1240px] flex-col items-center justify-between gap-3 px-6 py-8 text-xs text-muted-foreground sm:flex-row">
          <span className="flex items-center gap-2">
            <LogoMark size={20} />
            <span className="font-display text-sm text-foreground">Resolvyn</span>
            <span>Every answer is verified before it is said.</span>
          </span>
          <span>Nova Retail is a demo business. All customer, order and payment data is simulated.</span>
        </div>
      </footer>
    </div>
  );
}
