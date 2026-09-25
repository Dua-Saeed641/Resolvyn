"use client";

import { useEffect, useMemo, useState } from "react";

import { AppShell } from "@/components/layout/AppShell";
import { TicketCard } from "@/components/ops/TicketCard";
import { EmptyState } from "@/components/ui/EmptyState";
import { inputCls } from "@/components/ui/primitives";
import { useLive } from "@/lib/live";
import { cx } from "@/lib/utils";

/** project.md §32: All / Active / Waiting / Resolved / Needs Human / High Risk + agent, intent, sentiment, priority. */
const FILTERS = [
  { id: "all", label: "All" },
  { id: "active", label: "Active" },
  { id: "waiting", label: "Waiting" },
  { id: "resolved", label: "Resolved" },
  { id: "human", label: "Needs human" },
  { id: "risk", label: "High risk" },
  { id: "bug", label: "First-time bugs" },
] as const;

export default function TicketsPage() {
  const { tickets, approvals } = useLive();
  const [filter, setFilter] = useState<(typeof FILTERS)[number]["id"]>("all");
  const [agent, setAgent] = useState("");
  const [sentiment, setSentiment] = useState("");
  const [q, setQ] = useState("");
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 5000);
    return () => clearInterval(t);
  }, []);

  const all = useMemo(() => Object.values(tickets).sort((a, b) => (a.created_at < b.created_at ? 1 : -1)), [tickets]);
  const shown = all.filter((t) => {
    if (filter === "active" && ["RESOLVED", "FAILED", "WAITING_FOR_HUMAN"].includes(t.status)) return false;
    if (filter === "waiting" && t.status !== "WAITING_FOR_HUMAN") return false;
    if (filter === "resolved" && t.status !== "RESOLVED") return false;
    if (filter === "human" && !t.needs_human) return false;
    if (filter === "risk" && !["HIGH", "CRITICAL"].includes(t.priority)) return false;
    if (filter === "bug" && !t.is_first_time_bug) return false;
    if (agent && t.assigned_agent !== agent) return false;
    if (sentiment && t.sentiment !== sentiment) return false;
    if (q) {
      const hay = `${t.ticket_id} ${t.customer_name} ${t.subject} ${t.intent} ${t.assigned_agent} ${t.one_line_summary}`.toLowerCase();
      if (!hay.includes(q.toLowerCase())) return false;
    }
    return true;
  });

  const pendingByTicket = useMemo(() => {
    const m: Record<string, (typeof approvals)[number]> = {};
    for (const a of approvals) if (a.status === "PENDING" && !m[a.ticket_id]) m[a.ticket_id] = a;
    return m;
  }, [approvals]);

  return (
    <AppShell title="Tickets">
      <div className="mx-auto max-w-[1400px] space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <div role="tablist" className="flex gap-1 rounded-lg border border-border bg-card p-1">
            {FILTERS.map((f) => (
              <button
                key={f.id}
                role="tab"
                aria-selected={filter === f.id}
                onClick={() => setFilter(f.id)}
                className={cx("rounded px-2.5 py-1 text-xs font-medium", filter === f.id ? "bg-primary text-primary-foreground" : "text-text-muted hover:text-text-primary")}
              >
                {f.label}
              </button>
            ))}
          </div>
          <select aria-label="Agent" className={cx(inputCls, "w-auto py-1.5 text-xs")} value={agent} onChange={(e) => setAgent(e.target.value)}>
            <option value="">All agents</option>
            {["Technical", "Billing", "Account", "Order", "Other"].map((a) => (
              <option key={a}>{a}</option>
            ))}
          </select>
          <select aria-label="Sentiment" className={cx(inputCls, "w-auto py-1.5 text-xs")} value={sentiment} onChange={(e) => setSentiment(e.target.value)}>
            <option value="">Any sentiment</option>
            {["Positive", "Neutral", "Frustrated", "Angry"].map((a) => (
              <option key={a}>{a}</option>
            ))}
          </select>
          <input aria-label="Search tickets" className={cx(inputCls, "ml-auto w-64 py-1.5 text-xs")} placeholder="Search ticket, customer, intent, agent…" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>

        {shown.length === 0 ? (
          <EmptyState title="No tickets match" description={all.length ? "Change the filters to see more tickets." : "No support tickets yet. Start a call on the customer side or run a demo from the Overview."} />
        ) : (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
            {shown.map((t) => (
              <TicketCard key={t.ticket_id} ticket={t} now={now} pending={pendingByTicket[t.ticket_id] ?? null} />
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}
