/** project.md §54: every page needs a meaningful empty state, not blank space. */
export function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className="rounded border border-border bg-card px-6 py-10 text-center">
      <p className="text-sm font-medium text-text-primary">{title}</p>
      <p className="mt-1 text-sm text-text-muted">{description}</p>
    </div>
  );
}
