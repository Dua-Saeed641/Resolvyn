import { AppShell } from "@/components/layout/AppShell";
import { EmptyState } from "@/components/ui/EmptyState";

/** project.md §14, §37: system-wide event stream. Backed by /api/activity
 * once agent_events are persisted (docs/architecture.md §3 mapping table). */
export default function ActivityPage() {
  return (
    <AppShell title="Activity">
      <EmptyState title="No recent activity" description="System events will appear here as tickets are worked." />
    </AppShell>
  );
}
