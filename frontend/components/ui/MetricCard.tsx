/** project.md §12: compact operational metric, not a marketing stat card. */
export function MetricCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded border border-border bg-card px-4 py-3">
      <p className="text-xs uppercase tracking-wide text-text-muted">{label}</p>
      <p className="mt-1 text-xl font-semibold text-text-primary">{value}</p>
    </div>
  );
}
