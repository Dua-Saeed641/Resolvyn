"use client";

import { Check } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import type { CustomerTicketView } from "@/features/types";
import { CUSTOMER_STEPS, STATUS_COLOR, type TicketStatus } from "@/lib/constants";
import { fmtClock } from "@/lib/format";
import { cn } from "@/lib/utils";

const ACTION_LABEL: Record<string, string> = { PENDING: "Waiting for approval", APPROVED: "Approved", REJECTED: "Not approved", EXECUTED: "Done", FAILED: "Failed" };

function stepIndex(status: TicketStatus): number {
  const i = CUSTOMER_STEPS.findIndex((s) => s.key.includes(status));
  return i === -1 ? 0 : i;
}

/** The caller's ticket, updated in real time. Customer-safe: no confidence, no internal summary, no tool payloads. */
export function TicketPanel({ ticket }: { ticket: CustomerTicketView }) {
  const idx = stepIndex(ticket.status);
  const failed = ticket.status === "FAILED";
  const tone = STATUS_COLOR[ticket.status];
  return (
    <Card className="animate-fade-in" aria-label="Your ticket">
      <div className="flex items-start justify-between gap-3 p-5">
        <div className="min-w-0">
          <p className="text-xs font-medium text-muted-foreground">Your ticket</p>
          <p className="text-lg font-semibold tracking-tight">{ticket.ticket_id}</p>
          <p className="mt-0.5 truncate text-sm text-muted-foreground">{ticket.subject === "New conversation" ? "Tell us what happened, we are listening." : ticket.subject}</p>
        </div>
        <Badge variant={tone}>
          {ticket.status === "RESOLVED" ? <Check className="h-3 w-3" /> : <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden />}
          {ticket.status_label}
        </Badge>
      </div>

      <ol className="flex items-start px-5 pb-5" aria-label="Progress">
        {CUSTOMER_STEPS.map((s, i) => {
          const done = i < idx || (i === idx && ticket.status === "RESOLVED");
          const current = i === idx && !done;
          return (
            <li key={s.label} className="relative flex min-w-0 flex-1 flex-col items-center text-center">
              {i > 0 && <span className={cn("absolute right-1/2 top-3 h-px w-full", i <= idx ? "bg-primary" : "bg-border")} aria-hidden />}
              <span
                className={cn(
                  "relative z-10 flex h-6 w-6 items-center justify-center rounded-full border text-[11px] font-medium",
                  failed && current ? "border-danger bg-danger text-white" : done ? "border-primary bg-primary text-primary-foreground" : current ? "border-primary bg-card text-foreground ring-4 ring-primary/10" : "border-border bg-card text-muted-foreground",
                )}
              >
                {done ? <Check className="h-3 w-3" /> : i + 1}
              </span>
              <span className={cn("mt-1.5 line-clamp-2 px-0.5 text-[10px] leading-tight", i <= idx ? "text-foreground" : "text-muted-foreground")}>{s.label}</span>
            </li>
          );
        })}
      </ol>

      <Separator />
      <div className="space-y-4 p-5">
        <dl className="grid grid-cols-2 gap-x-6 gap-y-1.5 text-[13px]">
          <dt className="text-muted-foreground">Handled by</dt>
          <dd className="text-right font-medium">{ticket.department ? `${ticket.department} team` : "Assigning…"}</dd>
          {ticket.escalated || ticket.needs_human ? (
            <>
              <dt className="text-muted-foreground">Team member</dt>
              <dd className="text-right font-medium text-warning">Looking at this now</dd>
            </>
          ) : null}
        </dl>

        {ticket.actions.length > 0 && (
          <ul className="space-y-2">
            {ticket.actions.map((a, i) => (
              <li key={i} className="flex items-center justify-between gap-3 rounded-md border bg-muted/40 px-3 py-2 text-[13px]">
                <span className="min-w-0 truncate">{a.summary}</span>
                <Badge variant={a.status === "PENDING" ? "warning" : a.status === "REJECTED" || a.status === "FAILED" ? "danger" : "success"}>{ACTION_LABEL[a.status] ?? a.status}</Badge>
              </li>
            ))}
          </ul>
        )}

        <div>
          <p className="mb-2 text-xs font-medium text-muted-foreground">What is happening</p>
          {ticket.timeline.length === 0 ? (
            <p className="text-sm text-muted-foreground">Nothing yet.</p>
          ) : (
            <ol className="space-y-2">
              {[...ticket.timeline].reverse().map((t, i) => (
                <li key={i} className="animate-fade-in grid grid-cols-[62px_1fr] gap-2 text-[13px]">
                  <time className="tabular-nums text-xs text-muted-foreground">{fmtClock(t.time)}</time>
                  <span>{t.text}</span>
                </li>
              ))}
            </ol>
          )}
        </div>
      </div>
    </Card>
  );
}
