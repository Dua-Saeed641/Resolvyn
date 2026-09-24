import { GlobalSearch } from "@/components/layout/GlobalSearch";
import { NotificationBell } from "@/components/layout/NotificationBell";
import { SystemStatus } from "@/components/layout/SystemStatus";

/** project.md §11; spec §5: page title left, search/notifications/status/operator right. */
export function TopBar({ title }: { title: string }) {
  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-border px-6">
      <p className="text-sm font-medium text-text-primary">{title}</p>
      <div className="flex items-center gap-5 text-xs text-text-muted">
        <GlobalSearch />
        <NotificationBell />
        <SystemStatus />
      </div>
    </header>
  );
}
