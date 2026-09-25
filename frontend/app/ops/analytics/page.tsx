"use client";

import { AppShell } from "@/components/layout/AppShell";
import { DepartmentBars } from "@/components/ops/charts/DepartmentBars";
import { RankedBars } from "@/components/ops/charts/RankedBars";
import { SentimentBreakdown } from "@/components/ops/charts/SentimentBreakdown";
import { TrendChart } from "@/components/ops/charts/TrendChart";
import { Card } from "@/components/ui/primitives";
import { MetricCard } from "@/components/ui/MetricCard";
import { fmtDuration } from "@/lib/format";
import { useLive } from "@/lib/live";

/** project.md §66-67: simple, monochrome dashboard — now with real charts
 *  (dataviz skill) instead of plain bars, still no chart-junk: one hue per
 *  chart unless the category is a small fixed set (department), gridlines
 *  hairline and recessive, values labeled at the mark rather than hidden
 *  behind hover-only tooltips. Everything here is the same /api/analytics
 *  snapshot the ops WebSocket already pushes every few seconds — no polling,
 *  no separate "live" mode toggle needed. */
export default function AnalyticsPage() {
  const { stats, connected } = useLive();
  return (
    <AppShell title="Analytics">
      <div className="mx-auto max-w-[1200px] space-y-6">
        <div className="flex items-center justify-between">
          <p className="text-xs text-text-muted">Updates automatically as tickets move — no refresh needed.</p>
          <span className="flex items-center gap-1.5 text-xs text-text-muted">
            <span className={`h-1.5 w-1.5 rounded-full ${connected ? "bg-success" : "bg-text-secondary"}`} aria-hidden />
            {connected ? "Live" : "Reconnecting…"}
          </span>
        </div>

        <div className="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-6">
          <MetricCard label="Tickets" value={stats?.tickets_total ?? "—"} />
          <MetricCard label="Resolved" value={stats?.resolved ?? "—"} tone="success" />
          <MetricCard label="Active" value={stats?.active ?? "—"} />
          <MetricCard label="Handled by AI" value={stats?.handled_by_ai ?? "—"} hint={stats?.ai_resolution_rate != null ? `${stats.ai_resolution_rate}% of resolved` : undefined} />
          <MetricCard label="Human interventions" value={stats?.human_interventions ?? "—"} />
          <MetricCard label="Avg resolution" value={fmtDuration(stats?.avg_resolution_seconds)} />
        </div>

        <Card title="Ticket volume">
          <TrendChart data={stats?.volume_by_hour ?? Array.from({ length: 24 }, (_, i) => ({ label: `${i}:00`, count: 0 }))} />
        </Card>

        <div className="grid gap-6 lg:grid-cols-2">
          <Card title="Tickets by department"><DepartmentBars data={stats?.agent_activity ?? {}} /></Card>
          <Card title="Customer sentiment"><SentimentBreakdown data={stats?.sentiment ?? {}} /></Card>
          <Card title="Ticket intents" subtitle="What customers are contacting support about"><RankedBars data={stats?.intents ?? {}} /></Card>
          <Card title="Resolution paths" subtitle="How each ticket was handled"><RankedBars data={stats?.paths ?? {}} /></Card>
          <Card title="Human interventions by type"><RankedBars data={stats?.human_by_type ?? {}} /></Card>
        </div>
      </div>
    </AppShell>
  );
}
