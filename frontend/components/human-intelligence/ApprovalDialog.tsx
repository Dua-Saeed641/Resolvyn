/** project.md §24: human approval gate for a proposed AI action. */
export function ApprovalDialog({
  summary,
  reason,
  confidence,
  onApprove,
  onReject,
}: {
  summary: string;
  reason: string;
  confidence: number;
  onApprove: () => void;
  onReject: () => void;
}) {
  return (
    <div className="rounded border border-warning/30 bg-card p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-warning">Action requires approval</p>
      <p className="mt-2 text-sm text-text-primary">{summary}</p>
      <p className="mt-1 text-xs text-text-muted">
        {reason} · Confidence {confidence}%
      </p>
      <div className="mt-3 flex gap-2">
        <button onClick={onApprove} className="rounded bg-text-primary px-3 py-1.5 text-xs font-medium text-bg-primary">
          Approve
        </button>
        <button onClick={onReject} className="rounded border border-border px-3 py-1.5 text-xs font-medium text-text-primary">
          Reject
        </button>
      </div>
    </div>
  );
}
