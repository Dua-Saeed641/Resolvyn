import { AppShell } from "@/components/layout/AppShell";
import { MetricCard } from "@/components/ui/MetricCard";
import type { AnalyticsSummary } from "@/features/analytics/types";
import { api } from "@/lib/api";

/** project.md §66-67: aggregate metrics, monochrome charts. */
export default async function AnalyticsPage() {
  const summary = await api.get<AnalyticsSummary>("/analytics").catch(() => null);

  return (
    <AppShell title="Analytics">
      <div className="grid grid-cols-4 gap-3">
        <MetricCard label="Tickets today" value={summary?.tickets_today ?? 0} />
        <MetricCard label="Resolved" value={summary?.resolved ?? 0} />
        <MetricCard label="Active" value={summary?.active ?? 0} />
        <MetricCard label="Human interventions" value={summary?.human_interventions ?? 0} />
      </div>
    </AppShell>
  );
}
