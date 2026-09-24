import { PRIORITY_COLOR, type Priority } from "@/lib/constants";
import { cx } from "@/lib/utils";

const COLOR_CLASSES = {
  danger: "text-danger",
  warning: "text-warning",
  muted: "text-text-muted",
} as const;

/** spec §37: only HIGH/CRITICAL should stand out. */
export function PriorityBadge({ priority }: { priority: Priority }) {
  return <span className={cx("text-xs font-medium", COLOR_CLASSES[PRIORITY_COLOR[priority]])}>{priority}</span>;
}
