import Link from "next/link";

import { AppShell } from "@/components/layout/AppShell";
import { LearningSignalCard } from "@/components/learning/LearningSignalCard";
import { EmptyState } from "@/components/ui/EmptyState";
import { StatusBadge } from "@/components/ui/StatusBadge";
import type { LearningSignal } from "@/features/learning/types";
import type { TicketStatus } from "@/lib/constants";
import { api } from "@/lib/api";
import { cx, formatClock } from "@/lib/utils";

interface PredictionError {
  signal_id: number;
  ticket_id: string;
  expected: string | null;
  observed: string | null;
  signal_type: string;
  timestamp: string;
}

interface Outcome {
  ticket_id: string;
  status: TicketStatus;
  priority: string;
  confidence: number | null;
  resolution_time: number | null;
}

const TABS = [
  { label: "Learning Signals", value: "signals" },
  { label: "Prediction Errors", value: "prediction-errors" },
  { label: "Outcomes", value: "outcomes" },
] as const;

/** spec §29-30: how human interactions become durable learning artifacts —
 * presented as prediction-error-style events, never claimed as trained RL. */
export default async function LearningSignalsPage({ searchParams }: { searchParams: { view?: string } }) {
  const activeTab = TABS.find((t) => t.value === searchParams.view) ?? TABS[0];

  return (
    <AppShell title="Learning Signals">
      <div className="mb-4 flex gap-1 border-b border-border">
        {TABS.map((tab) => (
          <Link
            key={tab.value}
            href={`/learning-signals?view=${tab.value}`}
            className={cx(
              "border-b-2 px-3 py-2 text-sm",
              activeTab.value === tab.value ? "border-text-primary text-text-primary" : "border-transparent text-text-muted hover:text-text-body"
            )}
          >
            {tab.label}
          </Link>
        ))}
      </div>

      {activeTab.value === "signals" && <SignalsView />}
      {activeTab.value === "prediction-errors" && <PredictionErrorsView />}
      {activeTab.value === "outcomes" && <OutcomesView />}
    </AppShell>
  );
}

async function SignalsView() {
  const signals = await api.get<LearningSignal[]>("/learning-signals").catch(() => [] as LearningSignal[]);
  if (signals.length === 0) {
    return <EmptyState title="No learning signals yet" description="Signals are recorded from human correction, override, or teaching events." />;
  }
  return (
    <div className="grid grid-cols-2 gap-3">
      {signals.map((s) => (
        <LearningSignalCard key={s.signal_id} signal={s} />
      ))}
    </div>
  );
}

async function PredictionErrorsView() {
  const errors = await api.get<PredictionError[]>("/learning-signals?view=prediction-errors").catch(() => [] as PredictionError[]);
  if (errors.length === 0) {
    return <EmptyState title="No prediction errors yet" description="A prediction error is recorded when a human correction or override diverges from the AI's decision." />;
  }
  return (
    <div className="flex flex-col gap-3">
      {errors.map((e) => (
        <div key={e.signal_id} className="rounded border border-border bg-card p-4 text-sm">
          <p className="text-xs font-medium uppercase tracking-wide text-text-muted">Prediction error</p>
          <dl className="mt-2 grid grid-cols-2 gap-y-1 text-xs">
            <dt className="text-text-muted">Expected</dt>
            <dd className="text-text-body">{e.expected ?? "—"}</dd>
            <dt className="text-text-muted">Observed</dt>
            <dd className="text-text-body">{e.observed ?? "—"}</dd>
            <dt className="text-text-muted">Signal</dt>
            <dd className="text-text-body">{e.signal_type}</dd>
          </dl>
          <Link href={`/tickets/${e.ticket_id}`} className="mt-2 inline-block text-xs text-text-muted hover:text-text-primary">
            {e.ticket_id}
          </Link>
        </div>
      ))}
    </div>
  );
}

async function OutcomesView() {
  const outcomes = await api.get<Outcome[]>("/learning-signals?view=outcomes").catch(() => [] as Outcome[]);
  if (outcomes.length === 0) {
    return <EmptyState title="No outcomes yet" description="Resolved and failed tickets will appear here." />;
  }
  return (
    <div className="rounded border border-border">
      {outcomes.map((o) => (
        <div key={o.ticket_id} className="grid grid-cols-[100px_140px_100px_100px_1fr] items-center gap-3 border-b border-border px-4 py-3 text-sm last:border-b-0">
          <Link href={`/tickets/${o.ticket_id}`} className="font-medium text-text-primary hover:underline">
            {o.ticket_id}
          </Link>
          <StatusBadge status={o.status} />
          <span className="text-text-muted">{o.priority}</span>
          <span className="text-text-muted">{o.confidence != null ? `${o.confidence}%` : "—"}</span>
          <span className="text-text-muted">{o.resolution_time != null ? `${o.resolution_time}s to resolve` : "—"}</span>
        </div>
      ))}
    </div>
  );
}
