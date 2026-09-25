"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/layout/AppShell";
import { EmptyState } from "@/components/ui/EmptyState";
import { Pill } from "@/components/ui/StatusBadge";
import { api } from "@/lib/api";
import { fmtDateTime } from "@/lib/format";
import { cx } from "@/lib/utils";

interface RoutingCandidate {
  agent: string;
  activation_score: number;
}

interface RoutingDecision {
  ticket_id: string;
  issue: string;
  intent: string | null;
  candidates: RoutingCandidate[];
  winner: string;
  runner_up: string | null;
  activation_gap: number;
  ambiguous: boolean;
  reason: string;
  timestamp: string;
}

/** Every ticket's fruit-fly-inspired mixture-of-experts routing decision
 *  (agents/swarm_router.py, docs/swarm-router.md) — a bio-inspired software
 *  routing mechanism, not a biological simulation. */
export default function RoutingPage() {
  const [decisions, setDecisions] = useState<RoutingDecision[] | null>(null);

  useEffect(() => {
    api.get<RoutingDecision[]>("/routing").then(setDecisions).catch(() => setDecisions([]));
  }, []);

  return (
    <AppShell title="Routing">
      <div className="mx-auto max-w-[1100px] space-y-4">
        <p className="text-sm text-text-muted">
          Every department competes on a cheap, deterministic activation score; the winner is the only one that becomes active. Ambiguous cases (a narrow lead, or no strong match) pause for a
          teammate to GUIDE instead of guessing.
        </p>
        {decisions === null ? (
          <p className="text-sm text-text-muted">Loading…</p>
        ) : decisions.length === 0 ? (
          <EmptyState title="No routing decisions yet" description="A routing decision appears here as soon as a ticket reaches the swarm router." />
        ) : (
          decisions.map((d) => (
            <article key={d.ticket_id} className="animate-fade-in rounded-lg border border-border bg-card p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-3">
                  <Link href={`/ops/tickets/${d.ticket_id}`} className="text-sm font-medium text-text-primary underline-offset-2 hover:underline">
                    {d.ticket_id}
                  </Link>
                  <span className="text-[13px] text-text-body">{d.issue}</span>
                  {d.intent && <Pill>{d.intent}</Pill>}
                </div>
                <span className="text-xs text-text-secondary">{fmtDateTime(d.timestamp)}</span>
              </div>

              <div className="mt-3 grid gap-x-6 gap-y-1.5 sm:grid-cols-2 lg:grid-cols-3">
                {[...d.candidates].sort((a, b) => b.activation_score - a.activation_score).map((c) => (
                  <div key={c.agent} className="flex items-center gap-2 text-[13px]">
                    <span className={cx("w-20 shrink-0", c.agent === d.winner && !d.ambiguous ? "font-medium text-text-primary" : "text-text-muted")}>
                      {c.agent}
                    </span>
                    <div className="h-1.5 flex-1 overflow-hidden rounded bg-border">
                      <div
                        className={cx("h-full rounded", c.agent === d.winner && !d.ambiguous ? "bg-success" : "bg-text-muted")}
                        style={{ width: `${Math.round(c.activation_score * 100)}%` }}
                      />
                    </div>
                    <span className="w-10 shrink-0 text-right tabular-nums text-text-secondary">{c.activation_score.toFixed(2)}</span>
                  </div>
                ))}
              </div>

              <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-border pt-2 text-xs">
                {d.ambiguous ? (
                  <Pill tone="warning">Ambiguous — {d.winner} vs {d.runner_up ?? "—"}</Pill>
                ) : (
                  <Pill tone="success">Winner · {d.winner}</Pill>
                )}
                <span className="text-text-muted">Gap {d.activation_gap.toFixed(2)} · {d.reason}</span>
              </div>
            </article>
          ))
        )}
      </div>
    </AppShell>
  );
}
