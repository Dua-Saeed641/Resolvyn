"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { LogoMark } from "@/components/brand/Logo";
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

/** Customer side: talk to Riya, chat, or email, and watch the ticket update in real time. */
export default function CustomerPage() {
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
      <header className="sticky top-0 z-20 border-b bg-card/90 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-[1180px] items-center justify-between px-4">
          <div className="flex items-center gap-2.5">
            <LogoMark size={34} />
            <div>
              <p className="text-sm font-semibold leading-tight tracking-tight">Nova Retail</p>
              <p className="text-[11px] leading-tight text-muted-foreground">Customer support · powered by Resolvyn</p>
            </div>
          </div>
          <div className="flex items-center gap-1.5">
            <ThemeToggle />
            <Button variant="outline" size="sm" asChild>
              <Link href="/ops">Team console</Link>
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1180px] px-4 py-8">
        <div className="mb-6">
          <h1 className="text-2xl font-semibold tracking-tight">How can we help?</h1>
          <p className="mt-1 max-w-xl text-sm text-muted-foreground">Talk to Riya, chat with her, or send an email. She can look at your orders and payments and sort most things out straight away.</p>
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
                <p className="text-sm font-medium">Your ticket appears here</p>
                <p className="mx-auto mt-1 max-w-sm text-sm text-muted-foreground">A ticket is created the moment you start, and its status updates live while you talk.</p>
              </Card>
            )}

            <Card aria-label="Your tickets">
              <div className="border-b px-5 py-3.5">
                <h2 className="text-sm font-semibold tracking-tight">{me ? `${me.name.split(" ")[0]}'s tickets` : "Your tickets"}</h2>
              </div>
              {history.length === 0 ? (
                <p className="p-5 text-sm text-muted-foreground">No tickets yet.</p>
              ) : (
                <ul>
                  {history.slice(0, 8).map((t) => (
                    <li key={t.ticket_id} className={cn("flex items-center justify-between gap-3 border-b px-5 py-3 text-[13px] last:border-b-0", t.ticket_id === currentId && "bg-muted/50")}>
                      <span className="min-w-0">
                        <span className="block truncate">
                          <span className="mr-2 font-medium">{t.ticket_id}</span>
                          {t.subject}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {fmtDateTime(t.created_at)} · {t.status_label}
                        </span>
                      </span>
                      <StatusBadge status={t.status} />
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          </div>
        </div>

        <footer className="mt-10 flex items-center justify-center gap-2 border-t pt-6 text-xs text-muted-foreground">
          <LogoMark size={18} />
          <span>Powered by Resolvyn. Every answer is verified before it is said.</span>
        </footer>
      </main>
    </div>
  );
}
