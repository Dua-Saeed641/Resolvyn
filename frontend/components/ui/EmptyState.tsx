import type { ReactNode } from "react";

/** project.md §54: every page needs a meaningful empty state, not blank space. */
export function EmptyState({ title, description, action }: { title: string; description: string; action?: ReactNode }) {
  return (
    <div className="rounded-lg border border-dashed border-border bg-card px-6 py-10 text-center">
      <p className="text-sm font-medium text-text-primary">{title}</p>
      <p className="mx-auto mt-1 max-w-md text-sm text-text-muted">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
