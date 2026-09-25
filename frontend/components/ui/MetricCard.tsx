import { Card } from "@/components/ui/card";
import { cx } from "@/lib/utils";

/** Compact operational metric, not a marketing stat card. */
export function MetricCard({ label, value, hint, tone }: { label: string; value: string | number; hint?: string; tone?: "warning" | "danger" | "success" }) {
  return (
    <Card className="px-4 py-3.5">
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <p
        className={cx(
          "mt-1.5 font-display text-3xl font-normal tabular-nums tracking-tight text-foreground",
          tone === "warning" && "text-warning",
          tone === "danger" && "text-danger",
          tone === "success" && "text-success",
        )}
      >
        {value}
      </p>
      {hint && <p className="mt-0.5 truncate text-xs text-muted-foreground">{hint}</p>}
    </Card>
  );
}
