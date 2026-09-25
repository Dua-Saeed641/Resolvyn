"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import { AppShell } from "@/components/layout/AppShell";
import { BrainTrace } from "@/components/ops/BrainTrace";
import { KnowledgeSources, ToolCalls, Understanding } from "@/components/ops/AiOperations";
import { Conversation } from "@/components/ops/Conversation";
import { FirstTimeBugCard } from "@/components/ops/FirstTimeBugCard";
import { HumanActionPanel } from "@/components/ops/HumanActionPanel";
import { Timeline } from "@/components/ops/Timeline";
import { EmptyState } from "@/components/ui/EmptyState";
import { Card, Kv, Skeleton } from "@/components/ui/primitives";
import { Pill, StatusBadge } from "@/components/ui/StatusBadge";
import { fmtDateTime, fmtDuration } from "@/lib/format";
import { useTicketDetail } from "@/lib/useTicketDetail";

/** project.md §15: ticket workspace — conversation + AI operations + timeline — and the AI's
 *  live case notes so a human opening it mid-call sees exactly where the AI is
 *  (docs/architecture.md §2.5: one-line summary + detailed summary, team side only). */
export default function TicketDetailPage() {
  const { ticketId } = useParams<{ ticketId: string }>();
  const { detail: t, error } = useTicketDetail(ticketId);
  const [showDoc, setShowDoc] = useState(false);

  if (error && !t) {
    return (
      <AppShell title="Ticket">
        <EmptyState title="Ticket not found" description={error} action={<Link href="/ops/tickets" className="text-sm underline">Back to tickets</Link>} />
      </AppShell>
    );
  }
  if (!t) {
    return (
      <AppShell title="Ticket">
        <div className="space-y-4">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      </AppShell>
    );
  }

  const openBugs = t.bugs.filter((b) => b.status === "OPEN");
  const doneBugs = t.bugs.filter((b) => b.status !== "OPEN");

  return (
    <AppShell title={`Ticket ${t.ticket_id}`}>
      <div className="mx-auto max-w-[1400px] space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <Link href="/ops/tickets" className="text-sm text-text-muted hover:text-text-primary">
              ← Tickets
            </Link>
            <h1 className="text-lg font-semibold text-text-primary">{t.ticket_id}</h1>
            <StatusBadge status={t.status} />
            {t.call_active && <Pill tone="info">● Call in progress</Pill>}
            {t.is_first_time_bug && <Pill tone="danger">First-time bug</Pill>}
            {t.handled_by === "HUMAN" && <Pill tone="info">Human took over</Pill>}
          </div>
          <div className="flex items-center gap-2 text-xs text-text-muted">
            {t.jira_key && (
              <Pill>
                {t.jira_key} · {t.jira_status} · simulated
              </Pill>
            )}
            <span>Opened {fmtDateTime(t.created_at)}</span>
            {t.resolution_time != null && <span>· resolved in {fmtDuration(t.resolution_time)}</span>}
          </div>
        </div>

        {openBugs.map((b) => (
          <FirstTimeBugCard key={b.bug_id} bug={b} />
        ))}

        <div className="grid gap-5 lg:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)]">
          <div className="space-y-5">
            <Card title="AI case notes" subtitle="Written by the AI while the conversation is happening" right={<Pill tone={t.call_active ? "info" : "muted"}>{t.call_active ? "● Live" : t.status === "RESOLVED" ? "Final" : "Updated"}</Pill>}>
              <p className="text-[15px] font-medium leading-snug text-text-primary">{t.one_line_summary ?? "Waiting for the caller to describe the issue…"}</p>
              <p className="mt-2 text-[13px] leading-relaxed text-text-body">{t.detailed_summary ?? "The detailed summary appears here as soon as the conversation has content."}</p>
              {t.next_step && (
                <p className="mt-3 rounded border border-border bg-bg-secondary px-3 py-2 text-[13px]">
                  <span className="text-text-muted">Next step · </span>
                  <span className="text-text-primary">{t.next_step}</span>
                </p>
              )}
              {t.escalation_reason && (
                <p className="mt-2 text-xs text-warning">
                  Escalated{t.assignee ? ` to ${t.assignee}` : ""}: {t.escalation_reason}
                </p>
              )}
              {t.deep_summary && (
                <div className="mt-4 border-t border-border pt-3">
                  <p className="text-[11px] uppercase tracking-wide text-text-muted">Deep analysis · Qwen3.8-27B (epsilon deep tier)</p>
                  <p className="mt-1 text-[13px] leading-relaxed text-text-body">{t.deep_summary}</p>
                </div>
              )}
              {t.context_doc && (
                <div className="mt-4 border-t border-border pt-3">
                  <button onClick={() => setShowDoc(!showDoc)} className="text-xs text-text-muted underline underline-offset-2 hover:text-text-primary">
                    {showDoc ? "Hide" : "Open"} context document (simulated Confluence page)
                  </button>
                  {showDoc && <pre className="mt-2 max-h-80 overflow-auto whitespace-pre-wrap rounded border border-border bg-bg-secondary p-3 text-xs leading-relaxed text-text-body">{t.context_doc}</pre>}
                </div>
              )}
            </Card>

            <Card title="Live AI brain" subtitle="Every turn: heard → Jev → memory → decision → tools → truth guard → spoke" right={t.call_active ? <Pill tone="info">● Live</Pill> : undefined}>
              <BrainTrace events={t.events} />
            </Card>

            <Card title="Conversation" subtitle={`${t.channel} · ${t.customer_name ?? "Unidentified caller"}`}>
              <Conversation messages={t.messages} live={t.call_active} />
            </Card>
          </div>

          <div className="space-y-5">
            <Card title="Human intelligence" subtitle="Guide · Approve · Correct · Override · Teach">
              <HumanActionPanel t={t} />
            </Card>
            <Card title="Understanding">
              <Understanding t={t} />
            </Card>
            <Card title="Knowledge used" subtitle="Jev-written query → common memory + first-time-bug memory">
              <KnowledgeSources sources={t.knowledge} />
            </Card>
            <Card title="Tools">
              <ToolCalls calls={t.tool_calls} />
            </Card>
            {doneBugs.map((b) => (
              <FirstTimeBugCard key={b.bug_id} bug={b} />
            ))}
            {t.guidance.length > 0 && (
              <Card title="Guidance given to the AI">
                <ul className="list-inside list-disc space-y-1 text-[13px] text-text-body">
                  {t.guidance.map((g, i) => (
                    <li key={i}>{g}</li>
                  ))}
                </ul>
              </Card>
            )}
            {t.customer_id && (
              <Card title="Customer">
                <dl>
                  <Kv label="Name">{t.customer_name}</Kv>
                  <Kv label="Customer ID">{t.customer_id}</Kv>
                  <Kv label="Order">{t.order_id ?? "—"}</Kv>
                </dl>
                <Link href={`/ops/customers?id=${t.customer_id}`} className="mt-2 inline-block text-xs text-text-muted underline underline-offset-2 hover:text-text-primary">
                  Customer history
                </Link>
              </Card>
            )}
          </div>
        </div>

        <Card title="Activity timeline" subtitle="Ticket → intent → agent → knowledge → tool → decision → human action → outcome">
          <Timeline events={t.events} />
        </Card>
      </div>
    </AppShell>
  );
}
