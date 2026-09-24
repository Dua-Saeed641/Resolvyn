import type { LearningSignal } from "@/features/learning/types";

/** project.md §28: learning-event card. */
export function LearningSignalCard({ signal }: { signal: LearningSignal }) {
  return (
    <div className="rounded border border-border bg-card p-4 text-sm">
      <div className="flex items-center justify-between">
        <span className="font-medium text-text-primary">LS-{signal.signal_id}</span>
        <span className="text-text-muted">{signal.signal_type}</span>
      </div>
      <dl className="mt-3 space-y-1 text-xs">
        <div>
          <dt className="inline text-text-muted">Ticket </dt>
          <dd className="inline text-text-body">{signal.ticket_id}</dd>
        </div>
        {signal.expected_action ? (
          <div>
            <dt className="inline text-text-muted">AI decision </dt>
            <dd className="inline text-text-body">{signal.expected_action}</dd>
          </div>
        ) : null}
        {signal.observed_action ? (
          <div>
            <dt className="inline text-text-muted">Human correction </dt>
            <dd className="inline text-text-body">{signal.observed_action}</dd>
          </div>
        ) : null}
      </dl>
    </div>
  );
}
