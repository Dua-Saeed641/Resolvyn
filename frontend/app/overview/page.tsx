import Link from "next/link";

import { AppShell } from "@/components/layout/AppShell";
import { DemoControls } from "@/components/demo/DemoControls";
import { ActivityEvent } from "@/components/activity/ActivityEvent";
import { EmptyState } from "@/components/ui/EmptyState";
import { MetricCard } from "@/components/ui/MetricCard";
import { TicketTable } from "@/components/tickets/TicketTable";
import type { AnalyticsSummary } from "@/features/analytics/types";
import type { Customer } from "@/features/customers/types";
import type { Ticket, TicketEvent } from "@/features/tickets/types";
import { api } from "@/lib/api";
import { formatClock } from "@/lib/utils";

/** spec §7: command center — "what is happening across support right now." */
export default async function OverviewPage() {
  let tickets: Ticket[] = [];
  let customers: Customer[] = [];
  let summary: AnalyticsSummary | null = null;
  let activity: TicketEvent[] = [];
  let backendUnavailable = false;

  try {
    [tickets, customers, summary, activity] = await Promise.all([
      api.get<Ticket[]>("/tickets"),
      api.get<Customer[]>("/customers"),
      api.get<AnalyticsSummary>("/analytics"),
      api.get<TicketEvent[]>("/activity?limit=8"),
    ]);
  } catch {
    backendUnavailable = true;
  }

  return (
    <AppShell title="Overview">
      {backendUnavailable ? (
        <EmptyState
          title="Backend unavailable"
          description="Start the API (see backend/README.md) to see live ticket data."
        />
      ) : (
        <div className="flex flex-col gap-6">
          <div className="flex items-center justify-between">
            <div className="grid flex-1 grid-cols-5 gap-3">
              <MetricCard label="Active tickets" value={summary?.active ?? 0} />
              <MetricCard label="AI resolutions" value={summary?.resolved ?? 0} />
              <MetricCard label="Human interventions" value={summary?.human_interventions ?? 0} />
              <MetricCard
                label="Avg resolution"
                value={summary?.avg_resolution_seconds != null ? `${summary.avg_resolution_seconds}s` : "—"}
              />
              <MetricCard
                label="AI confidence"
                value={summary?.avg_confidence != null ? `${summary.avg_confidence}%` : "—"}
              />
            </div>
            <div className="ml-4">
              <DemoControls />
            </div>
          </div>

          <div className="grid grid-cols-[1fr_320px] gap-6">
            <div>
              <p className="text-sm font-medium text-text-primary">Live tickets</p>
              <p className="text-xs text-text-muted">Real-time support activity</p>
              <div className="mt-3">
                <TicketTable tickets={tickets} customers={customers} />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium text-text-primary">Live activity</p>
                <Link href="/activity" className="text-xs text-text-muted hover:text-text-primary">
                  View all
                </Link>
              </div>
              <div className="mt-3 rounded border border-border">
                {activity.length === 0 ? (
                  <EmptyState title="No recent activity" description="Events will appear as tickets are worked." />
                ) : (
                  activity.map((event) => (
                    <ActivityEvent
                      key={event.event_id}
                      timestamp={formatClock(event.timestamp)}
                      description={`${event.ticket_id} — ${event.description ?? event.event_type}`}
                    />
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
}
