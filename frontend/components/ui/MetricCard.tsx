import { cx } from "@/lib/utils";

/** project.md §12: compact operational metric, not a marketing stat card. */
export function MetricCard({ label, value, hint, tone }: { label: string; value: string | number; hint?: string; tone?: "warning" | "danger" | "success" }) {
  return (
    <div className="rounded-lg border border-border bg-card px-4 py-3">
      <p className="text-[11px] uppercase tracking-wide text-text-muted">{label}</p>
      <p
        className={cx(
          "mt-1 text-xl font-semibold tabular-nums text-text-primary",
          tone === "warning" && "text-warning",
          tone === "danger" && "text-danger",
          tone === "success" && "text-success",
        )}
      >
        {value}
      </p>
      {hint && <p className="mt-0.5 truncate text-[11px] text-text-secondary">{hint}</p>}
    </div>
  );
}
