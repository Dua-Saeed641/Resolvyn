import { AppShell } from "@/components/layout/AppShell";
import { ConfidenceIndicator } from "@/components/ui/ConfidenceIndicator";
import { EmptyState } from "@/components/ui/EmptyState";
import { api } from "@/lib/api";
import { formatClock } from "@/lib/utils";

interface RoutingDecision {
  ticket_id: string;
  issue: string;
  intent: string;
  destination: string;
  confidence: number | null;
  reason: string;
  timestamp: string;
}

/** spec §22: routing represented as a decision with a reason, not a dropdown. */
export default async function RoutingPage() {
  const decisions = await api.get<RoutingDecision[]>("/routing").catch(() => [] as RoutingDecision[]);

  return (
    <AppShell title="Routing">
      {decisions.length === 0 ? (
        <EmptyState title="No routing decisions" description="Routing decisions appear once tickets are classified." />
      ) : (
        <div className="rounded border border-border">
          <div className="grid grid-cols-[90px_1fr_140px_140px_90px_70px] gap-3 border-b border-border bg-card px-4 py-2 text-[11px] uppercase tracking-wide text-text-muted">
            <span>Ticket</span>
            <span>Issue / Reason</span>
            <span>Intent</span>
            <span>Destination</span>
            <span>Confidence</span>
            <span>Updated</span>
          </div>
          {decisions.map((d) => (
            <div key={d.ticket_id} className="grid grid-cols-[90px_1fr_140px_140px_90px_70px] items-start gap-3 border-b border-border px-4 py-3 text-sm last:border-b-0">
              <span className="font-medium text-text-primary">{d.ticket_id}</span>
              <div>
                <p className="text-text-body">{d.issue}</p>
                <p className="text-xs text-text-muted">{d.reason}</p>
              </div>
              <span className="text-text-muted">{d.intent}</span>
              <span className="text-text-body">{d.destination}</span>
              {d.confidence != null ? <ConfidenceIndicator confidence={d.confidence} /> : <span className="text-text-muted">—</span>}
              <span className="text-text-muted">{formatClock(d.timestamp)}</span>
            </div>
          ))}
        </div>
      )}
    </AppShell>
  );
}
