"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { AppShell } from "@/components/layout/AppShell";
import { ApprovalCard } from "@/components/ops/ApprovalCard";
import { BrainTrace } from "@/components/ops/BrainTrace";
import { FirstTimeBugCard } from "@/components/ops/FirstTimeBugCard";
import { Timeline } from "@/components/ops/Timeline";
import { TicketRow, TicketTableHeader } from "@/components/ops/TicketRow";
import { Button, Card } from "@/components/ui/primitives";
import { AgentStateBadge } from "@/components/ui/StatusBadge";
import { EmptyState } from "@/components/ui/EmptyState";
import { MetricCard } from "@/components/ui/MetricCard";
import { api } from "@/lib/api";
import { fmtDuration } from "@/lib/format";
import { useLive } from "@/lib/live";

const SCENARIOS = [
  { id: "duplicate_payment", title: "Duplicate payment → human-approved refund" },
  { id: "first_time_bug", title: "First-time bug → manager suggestion" },
  { id: "side_talk", title: "Caller talks to someone else mid-call" },
];

/** project.md §12-14: KPI row, live ticket stream, live activity. Plus the two human gates
 *  the architecture puts in front of the manager: approvals and first-time bugs. */
export default function OverviewPage() {
  const { tickets, stats, events, bugs, approvals, agents, demo } = useLive();
  const [now, setNow] = useState(() => Date.now());
  const [scenario, setScenario] = useState(SCENARIOS[0].id);
  const [autoHuman, setAutoHuman] = useState(true);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);

  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 5000);
    return () => clearInterval(t);
  }, []);

  const list = useMemo(
    () => Object.values(tickets).sort((a, b) => (a.updated_at < b.updated_at ? 1 : -1)),
    [tickets],
  );
  // the call the projector should explain: the live one, else the most recent that has turns
  const focus = list.find((t) => t.call_active) ?? list.find((t) => events.some((e) => e.ticket_id === t.ticket_id && e.event_type === "TURN_TRACE"));
  const focusEvents = focus ? events.filter((e) => e.ticket_id === focus.ticket_id) : [];
  const live = list.filter((t) => t.status !== "RESOLVED" || Date.now() - new Date(t.updated_at).getTime() < 600000);

  const runDemo = async () => {
    setBusy(true);
    setNote(null);
    try {
      const r = await api.post<{ started: boolean; reason?: string }>(`/demo/run/${scenario}?auto_human=${autoHuman}`);
      setNote(r.started ? "Demo call started. Watch the ticket appear below." : `Not started: ${r.reason}`);
    } catch (e) {
      setNote(e instanceof Error ? e.message : "Could not start the demo");
    } finally {
      setBusy(false);
    }
  };
  const reset = async () => {
    setBusy(true);
    try {
      await api.post("/demo/reset");
      setNote("Demo reset: live tickets, refunds and taught rules cleared.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <AppShell title="Overview">
      <div className="mx-auto max-w-[1400px] space-y-6">
        {(bugs.length > 0 || approvals.length > 0) && (
          <section aria-label="Needs a human" className="grid gap-4 lg:grid-cols-2">
            {bugs.map((b) => (
              <FirstTimeBugCard key={b.bug_id} bug={b} ticketId={b.ticket_id} compact />
            ))}
            {approvals.map((a) => (
              <ApprovalCard key={a.action_id} action={a} showLink />
            ))}
          </section>
        )}

        <section className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
          <MetricCard label="Active tickets" value={stats?.active ?? "—"} hint={`${stats?.live_calls ?? 0} live call(s)`} />
          <MetricCard label="AI resolutions" value={stats?.handled_by_ai ?? "—"} hint={stats?.ai_resolution_rate != null ? `${stats.ai_resolution_rate}% of resolved` : "handled without a human"} tone="success" />
          <MetricCard label="Escalated to humans" value={stats?.escalated ?? "—"} hint={`${stats?.waiting_for_human ?? 0} waiting now`} tone={stats && stats.waiting_for_human > 0 ? "warning" : undefined} />
          <MetricCard label="Human interventions" value={stats?.human_interventions ?? "—"} hint="guide · approve · correct · override · teach" />
          <MetricCard label="Avg resolution" value={fmtDuration(stats?.avg_resolution_seconds)} />
          <MetricCard label="AI confidence" value={stats?.avg_confidence != null ? `${stats.avg_confidence}%` : "—"} hint={`${stats?.first_time_bugs ?? 0} first-time bug(s)`} />
        </section>

        {focus && focusEvents.some((e) => e.event_type === "TURN_TRACE") && (
          <Card
            title={`Live AI brain · ${focus.ticket_id}${focus.customer_name ? ` · ${focus.customer_name}` : ""}`}
            subtitle="What the AI heard, how it judged it, what it recalled, what it decided, what it verified, and what it refused to say"
            right={
              <Link href={`/ops/tickets/${focus.ticket_id}`} className="text-xs text-text-muted underline underline-offset-2 hover:text-text-primary">
                {focus.call_active ? "● Live · open ticket" : "Open ticket"}
              </Link>
            }
          >
            <BrainTrace events={focusEvents} />
          </Card>
        )}

        <Card
          title="Live tickets"
          subtitle="Real-time support activity"
          bodyClass="p-0"
          right={<Link href="/ops/tickets" className="text-xs text-text-muted underline underline-offset-2 hover:text-text-primary">All tickets</Link>}
        >
          {live.length === 0 ? (
            <div className="p-4">
              <EmptyState title="No active tickets" description="All current conversations have been resolved. Start a call on the customer side, or run a demo." />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <div className="min-w-[1040px]">
                <TicketTableHeader />
                {live.slice(0, 8).map((t) => (
                  <TicketRow key={t.ticket_id} ticket={t} now={now} />
                ))}
              </div>
            </div>
          )}
        </Card>

        <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_440px]">
          <Card title="Live activity" subtitle="Every action is an event" bodyClass="max-h-[560px] overflow-y-auto">
            {events.length === 0 ? <p className="text-sm text-text-muted">No activity yet.</p> : <Timeline events={events.slice(0, 50)} showTicket newestFirst />}
          </Card>

          <div className="space-y-6">
            <Card title="Demo mode" subtitle="A scripted caller through the real pipeline (mock enterprise APIs)">
              <div className="space-y-3">
                <select aria-label="Scenario" value={scenario} onChange={(e) => setScenario(e.target.value)} className="w-full rounded border border-border bg-bg-secondary px-3 py-2 text-sm text-text-primary">
                  {SCENARIOS.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.title}
                    </option>
                  ))}
                </select>
                <label className="flex items-center gap-2 text-xs text-text-muted">
                  <input type="checkbox" checked={autoHuman} onChange={(e) => setAutoHuman(e.target.checked)} />
                  A scripted operator answers the approval / bug gates (untick to do it yourself)
                </label>
                <div className="flex gap-2">
                  <Button variant="primary" disabled={busy || demo?.state === "running"} onClick={runDemo}>
                    ▶ Run demo
                  </Button>
                  <Button disabled={busy} onClick={reset}>
                    Reset demo
                  </Button>
                </div>
                {demo?.state === "running" && <p className="text-xs text-info">Demo call in progress…</p>}
                {note && (
                  <p role="status" className="text-xs text-text-muted">
                    {note}
                  </p>
                )}
              </div>
            </Card>

            <Card title="Agents" subtitle="Deployed on the basis of the caller's query" bodyClass="p-0">
              <ul className="divide-y divide-border">
                {agents.map((a) => (
                  <li key={a.name} className="flex items-center justify-between gap-3 px-4 py-2.5">
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-text-primary">{a.name} Agent</p>
                      <p className="truncate text-[11px] text-text-muted">{a.current_ticket_id ? `${a.current_ticket_id} · ${a.current_operation ?? ""}` : `${a.current_tickets ?? 0} open · ${a.resolved_today} resolved`}</p>
                    </div>
                    <AgentStateBadge state={a.status} />
                  </li>
                ))}
              </ul>
            </Card>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
