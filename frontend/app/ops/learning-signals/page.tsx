"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/layout/AppShell";
import { Card } from "@/components/ui/primitives";
import { EmptyState } from "@/components/ui/EmptyState";
import { Pill } from "@/components/ui/StatusBadge";
import type { LearningSignal } from "@/features/types";
import { api } from "@/lib/api";
import { fmtDateTime } from "@/lib/format";
import { useLive } from "@/lib/live";

/** project.md §28-29: learning-EVENT records. Nothing here claims a model was retrained —
 *  behaviour changes because the Solvable Rulebook changed. */
export default function LearningSignalsPage() {
  const { subscribe } = useLive();
  const [signals, setSignals] = useState<LearningSignal[]>([]);
  useEffect(() => {
    api.get<LearningSignal[]>("/learning-signals").then(setSignals);
    return subscribe((e) => e.type === "learning_signal" && setSignals((p) => [e.signal, ...p.filter((s) => s.signal_id !== e.signal.signal_id)]));
  }, [subscribe]);

  return (
    <AppShell title="Learning Signals">
      <div className="mx-auto max-w-[1100px] space-y-4">
        <p className="text-sm text-text-muted">
          A signal is recorded when the expected outcome differs from what a human decided, or when a ticket is resolved. Corrections, suggestions and teaching also extend the Solvable Rulebook,
          which is what changes the AI&apos;s behaviour next time. No model is retrained.
        </p>
        {signals.length === 0 ? (
          <EmptyState title="No learning signals yet" description="Signals appear when a human approves, corrects, guides or teaches the AI, or when a ticket is resolved." />
        ) : (
          signals.map((s) => (
            <article key={s.signal_id} className="animate-fade-in rounded-lg border border-border bg-card p-4">
              <div className="flex items-center justify-between">
                <p className="text-xs font-medium text-text-muted">{s.code}</p>
                <span className="text-xs text-text-secondary">{fmtDateTime(s.timestamp)}</span>
              </div>
              <div className="mt-1 flex items-center gap-3">
                <p className="text-sm font-medium text-text-primary">{s.signal_type}</p>
                <Pill>Recorded</Pill>
                <Link href={`/ops/tickets/${s.ticket_id}`} className="text-xs text-text-muted underline underline-offset-2">
                  {s.ticket_id}
                </Link>
              </div>
              <div className="mt-3 grid gap-4 text-[13px] md:grid-cols-2">
                <div>
                  <p className="text-[11px] uppercase tracking-wide text-text-secondary">Expected · AI decision</p>
                  <p className="text-text-body">{s.expected_action ?? "—"}</p>
                </div>
                <div>
                  <p className="text-[11px] uppercase tracking-wide text-text-secondary">Observed · human / outcome</p>
                  <p className="text-text-primary">{s.observed_action ?? "—"}</p>
                </div>
              </div>
              {s.description && <p className="mt-2 text-xs text-text-muted">{s.description}</p>}
            </article>
          ))
        )}
      </div>
    </AppShell>
  );
}
