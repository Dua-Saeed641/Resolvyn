import type { HumanActionType } from "@/lib/constants";

/** project.md §22: the five human-intelligence entry points, shown together. */
const LABELS: Record<HumanActionType, string> = {
  GUIDE: "Guide",
  APPROVE: "Approve",
  CORRECT: "Correct",
  OVERRIDE: "Override",
  TEACH: "Teach",
};

export function HumanActionPanel({
  available,
  onSelect,
}: {
  available: HumanActionType[];
  onSelect: (action: HumanActionType) => void;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {available.map((action) => (
        <button
          key={action}
          onClick={() => onSelect(action)}
          className="rounded border border-border bg-card px-3 py-1.5 text-xs font-medium text-text-primary hover:border-text-muted"
        >
          {LABELS[action]}
        </button>
      ))}
    </div>
  );
}
