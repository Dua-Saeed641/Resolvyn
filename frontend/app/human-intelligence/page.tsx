import Link from "next/link";

import { AppShell } from "@/components/layout/AppShell";
import { EmptyState } from "@/components/ui/EmptyState";
import { EVENT_TYPE_LABEL } from "@/lib/constants";
import { api } from "@/lib/api";
import { cx, formatClock } from "@/lib/utils";

interface HumanActionRecord {
  human_event_id: number;
  ticket_id: string;
  event_type: string;
  previous_ai_action: string | null;
  human_action: string;
  reason: string | null;
  timestamp: string;
}

const TABS = [
  { label: "Interventions", value: "interventions" },
  { label: "Approvals", value: "approvals" },
  { label: "Corrections", value: "corrections" },
] as const;

/** spec §23: humans embedded in the workflow, not just an escalation log. */
export default async function HumanIntelligencePage({ searchParams }: { searchParams: { tab?: string } }) {
  const activeTab = TABS.find((t) => t.value === searchParams.tab) ?? TABS[0];
  const actions = await api
    .get<HumanActionRecord[]>(`/human-intelligence?tab=${activeTab.value}`)
    .catch(() => [] as HumanActionRecord[]);

  return (
    <AppShell title="Human Intelligence">
      <div className="mb-4 flex gap-1 border-b border-border">
        {TABS.map((tab) => (
          <Link
            key={tab.value}
            href={`/human-intelligence?tab=${tab.value}`}
            className={cx(
              "border-b-2 px-3 py-2 text-sm",
              activeTab.value === tab.value ? "border-text-primary text-text-primary" : "border-transparent text-text-muted hover:text-text-body"
            )}
          >
            {tab.label}
          </Link>
        ))}
      </div>

      {actions.length === 0 ? (
        <EmptyState title="No interventions yet" description="Guide, approval, correction, override, and teach events will appear here." />
      ) : (
        <div className="flex flex-col gap-3">
          {actions.map((a) => (
            <div key={a.human_event_id} className="rounded border border-border bg-card p-4 text-sm">
              <div className="flex items-center justify-between">
                <p className="font-medium text-text-primary">{EVENT_TYPE_LABEL[a.event_type] ?? a.event_type}</p>
                <Link href={`/tickets/${a.ticket_id}`} className="text-xs text-text-muted hover:text-text-primary">
                  {a.ticket_id}
                </Link>
              </div>
              {a.previous_ai_action && <p className="mt-1 text-xs text-text-muted">AI decision: {a.previous_ai_action}</p>}
              <p className="mt-1 text-xs text-text-body">{a.human_action}</p>
              {a.reason && <p className="mt-1 text-xs text-text-muted">Reason: {a.reason}</p>}
              <p className="mt-2 text-[11px] text-text-muted">{formatClock(a.timestamp)}</p>
            </div>
          ))}
        </div>
      )}
    </AppShell>
  );
}
