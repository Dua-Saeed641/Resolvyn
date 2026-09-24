"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { AppShell } from "@/components/layout/AppShell";
import { FirstTimeBugCard } from "@/components/ops/FirstTimeBugCard";
import { Card } from "@/components/ui/primitives";
import { EmptyState } from "@/components/ui/EmptyState";
import { MetricCard } from "@/components/ui/MetricCard";
import { Pill } from "@/components/ui/StatusBadge";
import type { FirstTimeBug, HumanAction } from "@/features/types";
import { api } from "@/lib/api";
import { fmtDateTime } from "@/lib/format";
import { useLive } from "@/lib/live";

const TYPES = [
  ["GUIDANCE", "Guide"],
  ["APPROVAL", "Approve"],
  ["CORRECTION", "Correct"],
  ["OVERRIDE", "Override"],
  ["TEACHING", "Teach"],
] as const;

/** project.md §79: how humans are embedded in the loop, and what the AI learned from each action. */
export default function HumanIntelligencePage() {
  const { subscribe } = useLive();
  const [data, setData] = useState<{ total: number; counts: Record<string, number>; actions: HumanAction[] } | null>(null);
  const [bugs, setBugs] = useState<FirstTimeBug[]>([]);
  const load = useCallback(() => {
    api.get<typeof data>("/human-intelligence").then(setData);
    api.get<FirstTimeBug[]>("/human-intelligence/bugs").then(setBugs);
  }, []);
  useEffect(() => {
    load();
    return subscribe((e) => (e.type === "human_action" || e.type === "bug_update" || e.type === "bug_alert") && load());
  }, [load, subscribe]);

  return (
    <AppShell title="Human Intelligence">
      <div className="mx-auto max-w-[1300px] space-y-6">
        <div className="grid grid-cols-2 gap-3 md:grid-cols-6">
          <MetricCard label="Interventions" value={data?.total ?? "—"} />
          {TYPES.map(([k, l]) => (
            <MetricCard key={k} label={l} value={data?.counts[k] ?? 0} />
          ))}
        </div>

        <Card title="First-time bugs" subtitle="Issues with no precedent in memory. The suggestion you give is added to the Solvable Rulebook.">
          {bugs.length === 0 ? (
            <p className="text-sm text-text-muted">No first-time bugs have been reported.</p>
          ) : (
            <div className="grid gap-4 lg:grid-cols-2">
              {bugs.map((b) => (
                <FirstTimeBugCard key={b.bug_id} bug={b} ticketId={b.ticket_id} compact />
              ))}
            </div>
          )}
        </Card>

        <Card title="Audit log" subtitle="Every human action, with the AI decision it changed" bodyClass="p-0">
          {!data || data.actions.length === 0 ? (
            <div className="p-4">
              <EmptyState title="No human actions yet" description="Guide, approve, correct, override or teach from a ticket and it is recorded here." />
            </div>
          ) : (
            data.actions.map((a) => (
              <div key={a.human_event_id} className="grid grid-cols-[120px_minmax(0,1fr)_minmax(0,1fr)_110px] gap-4 border-b border-border px-4 py-3 text-[13px] last:border-b-0">
                <div>
                  <Pill tone="info">{a.event_type}</Pill>
                  <p className="mt-1 text-[11px] text-text-secondary">{a.operator}</p>
                </div>
                <div>
                  <p className="text-[11px] uppercase tracking-wide text-text-secondary">AI decision</p>
                  <p className="text-text-body">{a.previous_ai_action ?? "—"}</p>
                </div>
                <div>
                  <p className="text-[11px] uppercase tracking-wide text-text-secondary">Human decision</p>
                  <p className="text-text-primary">{a.human_action}</p>
                  {a.reason && <p className="text-xs text-text-muted">Reason: {a.reason}</p>}
                </div>
                <div className="text-right text-xs text-text-muted">
                  {a.ticket_id ? <Link href={`/ops/tickets/${a.ticket_id}`} className="underline underline-offset-2">{a.ticket_id}</Link> : "Organisation-wide"}
                  <p>{fmtDateTime(a.timestamp)}</p>
                </div>
              </div>
            ))
          )}
        </Card>
      </div>
    </AppShell>
  );
}
