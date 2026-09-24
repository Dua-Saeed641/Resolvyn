/** project.md §11: page title left, system status + search right. */
export function TopBar({ title }: { title: string }) {
  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-border px-6">
      <p className="text-sm font-medium text-text-primary">{title}</p>
      <div className="flex items-center gap-4 text-xs text-text-muted">
        <span className="flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-success" aria-hidden />
          Operational
        </span>
        <span>Search</span>
      </div>
    </header>
  );
}
