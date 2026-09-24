"use client";

import { AppShell } from "@/components/layout/AppShell";
import { Timeline } from "@/components/ops/Timeline";
import { Card } from "@/components/ui/primitives";
import { EmptyState } from "@/components/ui/EmptyState";
import { useLive } from "@/lib/live";

/** project.md §14: the system event stream. Every important action produces an event (§65). */
export default function ActivityPage() {
  const { events } = useLive();
  return (
    <AppShell title="Activity">
      <div className="mx-auto max-w-[1100px]">
        <Card title="System activity" subtitle="Newest first · live">
          {events.length === 0 ? <EmptyState title="No activity yet" description="Events appear here as calls happen." /> : <Timeline events={events} showTicket newestFirst />}
        </Card>
      </div>
    </AppShell>
  );
}
