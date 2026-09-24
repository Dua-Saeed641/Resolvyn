"use client";

import { Pill } from "@/components/ui/StatusBadge";
import type { CustomerTicketView } from "@/features/types";
import { CUSTOMER_STEPS, STATUS_COLOR, type TicketStatus } from "@/lib/constants";
import { fmtClock } from "@/lib/format";
import { cx } from "@/lib/utils";

const ACTION_LABEL: Record<string, string> = { PENDING: "Waiting for approval", APPROVED: "Approved", REJECTED: "Not approved", EXECUTED: "Done", FAILED: "Failed" };

function stepIndex(status: TicketStatus): number {
  const i = CUSTOMER_STEPS.findIndex((s) => s.key.includes(status));
  return i === -1 ? 0 : i;
}

/** The caller's ticket, updated in real time (docs/architecture.md §2.4). Customer-safe:
 *  no confidence, no internal summary, no tool payloads. */
export function TicketPanel({ ticket }: { ticket: CustomerTicketView }) {
  const idx = stepIndex(ticket.status);
  const failed = ticket.status === "FAILED";
  const tone = STATUS_COLOR[ticket.status];
  return (
    <section className="animate-fade-in rounded-lg border border-border bg-card" aria-label="Your ticket">
      <header className="flex items-start justify-between gap-3 border-b border-border p-4">
        <div className="min-w-0">
          <p className="text-[11px] uppercase tracking-wide text-text-muted">Your ticket</p>
          <p className="text-lg font-semibold text-text-primary">{ticket.ticket_id}</p>
          <p className="mt-0.5 truncate text-sm text-text-body">{ticket.subject === "New conversation" ? "Tell us what happened — we are listening." : ticket.subject}</p>
        </div>
        <Pill tone={tone}>
          {ticket.status === "RESOLVED" ? "✓" : <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden />}
          {ticket.status_label}
        </Pill>
      </header>

      <ol className="grid grid-cols-5 gap-1 px-4 pt-4" aria-label="Progress">
        {CUSTOMER_STEPS.map((s, i) => (
          <li key={s.label} className="min-w-0">
            <div className={cx("h-1 rounded", failed ? "bg-danger" : i <= idx ? "bg-text-max" : "bg-border")} />
            <p className={cx("mt-1.5 truncate text-[10px] leading-tight", i <= idx ? "text-text-primary" : "text-text-secondary")}>{s.label}</p>
          </li>
        ))}
      </ol>

      <div className="space-y-3 p-4">
        <dl className="grid grid-cols-2 gap-x-6 gap-y-1 text-[13px]">
          <dt className="text-text-muted">Handled by</dt>
          <dd className="text-right text-text-primary">{ticket.department ? `${ticket.department} team` : "Assigning…"}</dd>
          {ticket.escalated || ticket.needs_human ? (
            <>
              <dt className="text-text-muted">Team member</dt>
              <dd className="text-right text-warning">Looking at this now</dd>
            </>
          ) : null}
        </dl>

        {ticket.actions.length > 0 && (
          <ul className="space-y-1.5">
            {ticket.actions.map((a, i) => (
              <li key={i} className="flex items-center justify-between gap-3 rounded border border-border bg-bg-secondary px-3 py-2 text-[13px]">
                <span className="min-w-0 truncate text-text-body">{a.summary}</span>
                <Pill tone={a.status === "PENDING" ? "warning" : a.status === "REJECTED" || a.status === "FAILED" ? "danger" : "success"}>{ACTION_LABEL[a.status] ?? a.status}</Pill>
              </li>
            ))}
          </ul>
        )}

        <div>
          <p className="mb-1 text-[11px] uppercase tracking-wide text-text-muted">What is happening</p>
          {ticket.timeline.length === 0 ? (
            <p className="text-sm text-text-muted">Nothing yet.</p>
          ) : (
            <ol className="space-y-1.5">
              {[...ticket.timeline].reverse().map((t, i) => (
                <li key={i} className="animate-fade-in grid grid-cols-[62px_1fr] gap-2 text-[13px]">
                  <time className="tabular-nums text-xs text-text-secondary">{fmtClock(t.time)}</time>
                  <span className="text-text-body">{t.text}</span>
                </li>
              ))}
            </ol>
          )}
        </div>
      </div>
    </section>
  );
}
