import { STATUS_COLOR, type TicketStatus } from "@/lib/constants";
import { cx } from "@/lib/utils";

/**
 * project.md §57: never rely on color alone — always pair it with a label.
 */
const COLOR_CLASSES = {
  success: "text-success border-success/30 bg-success/10",
  warning: "text-warning border-warning/30 bg-warning/10",
  danger: "text-danger border-danger/30 bg-danger/10",
  info: "text-info border-info/30 bg-info/10",
  muted: "text-text-muted border-border bg-card",
} as const;

export function StatusBadge({ status }: { status: TicketStatus }) {
  const color = STATUS_COLOR[status];
  return (
    <span
      className={cx(
        "inline-flex items-center gap-1.5 rounded border px-2 py-0.5 text-xs font-medium",
        COLOR_CLASSES[color]
      )}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden />
      {status.replaceAll("_", " ")}
    </span>
  );
}
