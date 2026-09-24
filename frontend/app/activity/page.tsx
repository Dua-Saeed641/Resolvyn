import Link from "next/link";

import { AppShell } from "@/components/layout/AppShell";
import { EmptyState } from "@/components/ui/EmptyState";
import type { TicketEvent } from "@/features/tickets/types";
import { api } from "@/lib/api";
import { formatClock } from "@/lib/utils";

/** spec §31: global chronological event stream, linked back to tickets.
 * Reachable from Overview's "Live activity" panel — not a top-level nav
 * item, matching the exact sidebar tree in spec §5. */
export default async function ActivityPage() {
  const events = await api.get<TicketEvent[]>("/activity?limit=100").catch(() => [] as TicketEvent[]);

  return (
    <AppShell title="Activity">
      {events.length === 0 ? (
        <EmptyState title="No recent activity" description="System events will appear here as tickets are worked." />
      ) : (
        <div className="rounded border border-border">
          {events.map((e) => (
            <div key={e.event_id} className="flex items-center gap-3 border-b border-border px-4 py-2 text-sm last:border-b-0">
              <span className="w-20 shrink-0 text-text-muted">{formatClock(e.timestamp)}</span>
              <Link href={`/tickets/${e.ticket_id}`} className="w-24 shrink-0 text-text-primary hover:underline">
                {e.ticket_id}
              </Link>
              <span className="w-32 shrink-0 truncate text-text-muted">{e.agent}</span>
              <span className="flex-1 truncate text-text-body">{e.description ?? e.event_type}</span>
            </div>
          ))}
        </div>
      )}
    </AppShell>
  );
}
