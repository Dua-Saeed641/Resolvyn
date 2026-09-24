"use client";

import { AppShell } from "@/components/layout/AppShell";
import { Card } from "@/components/ui/primitives";
import { MetricCard } from "@/components/ui/MetricCard";
import { fmtDuration } from "@/lib/format";
import { useLive } from "@/lib/live";

function Bars({ data }: { data: Record<string, number> }) {
  const entries = Object.entries(data);
  const max = Math.max(1, ...entries.map(([, v]) => v));
  if (!entries.length) return <p className="text-sm text-text-muted">No data yet.</p>;
  return (
    <ul className="space-y-2">
      {entries.map(([k, v]) => (
        <li key={k} className="grid grid-cols-[130px_1fr_32px] items-center gap-3 text-[13px]">
          <span className="truncate text-text-body">{k}</span>
          <span className="h-1.5 rounded bg-border" aria-hidden>
            <span className="block h-full rounded bg-text-body" style={{ width: `${(v / max) * 100}%` }} />
          </span>
          <span className="text-right tabular-nums text-text-primary">{v}</span>
        </li>
      ))}
    </ul>
  );
}

/** project.md §66-67: simple, monochrome. */
export default function AnalyticsPage() {
  const { stats } = useLive();
  return (
    <AppShell title="Analytics">
      <div className="mx-auto max-w-[1200px] space-y-6">
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-6">
          <MetricCard label="Tickets" value={stats?.tickets_total ?? "—"} />
          <MetricCard label="Resolved" value={stats?.resolved ?? "—"} tone="success" />
          <MetricCard label="Active" value={stats?.active ?? "—"} />
          <MetricCard label="Handled by AI" value={stats?.handled_by_ai ?? "—"} hint={stats?.ai_resolution_rate != null ? `${stats.ai_resolution_rate}% of resolved` : undefined} />
          <MetricCard label="Human interventions" value={stats?.human_interventions ?? "—"} />
          <MetricCard label="Avg resolution" value={fmtDuration(stats?.avg_resolution_seconds)} />
        </div>
        <div className="grid gap-6 lg:grid-cols-2">
          <Card title="Ticket intents"><Bars data={stats?.intents ?? {}} /></Card>
          <Card title="Agent activity"><Bars data={stats?.agent_activity ?? {}} /></Card>
          <Card title="Resolution paths" subtitle="How each ticket was handled"><Bars data={stats?.paths ?? {}} /></Card>
          <Card title="Human interventions by type"><Bars data={stats?.human_by_type ?? {}} /></Card>
        </div>
      </div>
    </AppShell>
  );
}
