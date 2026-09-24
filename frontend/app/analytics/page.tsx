import Link from "next/link";

import { AppShell } from "@/components/layout/AppShell";
import { MetricCard } from "@/components/ui/MetricCard";
import { StatusBadge } from "@/components/ui/StatusBadge";
import type {
  AgentPerformance,
  CustomerOutcome,
  HumanInterventionBreakdown,
  ResolutionBreakdown,
} from "@/features/analytics/types";
import type { TicketStatus } from "@/lib/constants";
import { api } from "@/lib/api";
import { cx } from "@/lib/utils";

const TABS = [
  { label: "Resolution", value: "resolution" },
  { label: "Agent Performance", value: "agent-performance" },
  { label: "Human Intervention", value: "human-intervention" },
  { label: "Customer Outcomes", value: "customer-outcomes" },
] as const;

/** spec §32-33: operational metrics only — monochrome, no decorative charts. */
export default async function AnalyticsPage({ searchParams }: { searchParams: { view?: string } }) {
  const activeTab = TABS.find((t) => t.value === searchParams.view) ?? TABS[0];

  return (
    <AppShell title="Analytics">
      <div className="mb-4 flex gap-1 border-b border-border">
        {TABS.map((tab) => (
          <Link
            key={tab.value}
            href={`/analytics?view=${tab.value}`}
            className={cx(
              "border-b-2 px-3 py-2 text-sm",
              activeTab.value === tab.value ? "border-text-primary text-text-primary" : "border-transparent text-text-muted hover:text-text-body"
            )}
          >
            {tab.label}
          </Link>
        ))}
      </div>

      {activeTab.value === "resolution" && <ResolutionView />}
      {activeTab.value === "agent-performance" && <AgentPerformanceView />}
      {activeTab.value === "human-intervention" && <HumanInterventionView />}
      {activeTab.value === "customer-outcomes" && <CustomerOutcomesView />}
    </AppShell>
  );
}

async function ResolutionView() {
  const data = await api.get<ResolutionBreakdown>("/analytics/resolution");
  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-2 gap-3">
        <MetricCard label="Resolved" value={data.resolved_count} />
        <MetricCard label="Avg resolution time" value={data.avg_resolution_seconds != null ? `${data.avg_resolution_seconds}s` : "—"} />
      </div>
      <div>
        <p className="mb-2 text-sm font-medium text-text-primary">Status distribution</p>
        <div className="flex flex-col gap-1.5">
          {Object.entries(data.status_distribution).map(([status, count]) => (
            <div key={status} className="flex items-center gap-3 text-xs">
              <span className="w-40 text-text-muted">{status}</span>
              <div className="h-2 flex-1 rounded bg-card">
                <div
                  className="h-2 rounded bg-text-primary"
                  style={{ width: `${(count / Math.max(...Object.values(data.status_distribution))) * 100}%` }}
                />
              </div>
              <span className="w-6 text-right text-text-body">{count}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

async function AgentPerformanceView() {
  const agents = await api.get<AgentPerformance[]>("/analytics/agent-performance");
  return (
    <div className="rounded border border-border">
      <div className="grid grid-cols-5 gap-3 border-b border-border bg-card px-4 py-2 text-[11px] uppercase tracking-wide text-text-muted">
        <span>Agent</span>
        <span>Status</span>
        <span>Handled</span>
        <span>Resolved</span>
        <span>Avg confidence</span>
      </div>
      {agents.map((a) => (
        <div key={a.agent} className="grid grid-cols-5 items-center gap-3 border-b border-border px-4 py-3 text-sm last:border-b-0">
          <span className="text-text-primary">{a.agent}</span>
          <span className="text-text-muted">{a.status}</span>
          <span className="text-text-body">{a.tickets_handled}</span>
          <span className="text-text-body">{a.resolved}</span>
          <span className="text-text-body">{a.avg_confidence != null ? `${a.avg_confidence}%` : "—"}</span>
        </div>
      ))}
    </div>
  );
}

async function HumanInterventionView() {
  const data = await api.get<HumanInterventionBreakdown>("/analytics/human-intervention");
  return (
    <div className="flex flex-col gap-6">
      <MetricCard label="Total interventions" value={data.total} />
      <div className="grid grid-cols-5 gap-3">
        {Object.entries(data.by_type).map(([type, count]) => (
          <MetricCard key={type} label={type} value={count} />
        ))}
      </div>
    </div>
  );
}

async function CustomerOutcomesView() {
  const outcomes = await api.get<CustomerOutcome[]>("/analytics/customer-outcomes");
  return (
    <div className="rounded border border-border">
      {outcomes.map((o) => (
        <div key={o.ticket_id} className="grid grid-cols-[100px_120px_140px_1fr] items-center gap-3 border-b border-border px-4 py-3 text-sm last:border-b-0">
          <span className="font-medium text-text-primary">{o.ticket_id}</span>
          <span className="text-text-muted">{o.customer_id}</span>
          <StatusBadge status={o.status as TicketStatus} />
          <span className="text-text-muted">{o.resolution_time != null ? `Resolved in ${o.resolution_time}s` : "—"}</span>
        </div>
      ))}
    </div>
  );
}
