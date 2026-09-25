import { confidenceLabel } from "@/lib/constants";

/** project.md §35: text + small indicator, never a giant progress bar. */
export function ConfidenceIndicator({ confidence }: { confidence: number }) {
  const label = confidenceLabel(confidence);
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-text-body">
      <span className="font-medium text-text-primary">{confidence}%</span>
      <span className="text-text-muted">{label}</span>
    </span>
  );
}
