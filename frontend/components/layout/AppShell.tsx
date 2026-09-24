import type { ReactNode } from "react";
import { Suspense } from "react";

import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import { RealtimeProvider } from "@/lib/realtime";

/** project.md §9: top bar + sidebar + main workspace three-part layout.
 * Wrapped in RealtimeProvider so every page picks up live backend state
 * (docs/architecture.md §3) without each page wiring its own socket. */
export function AppShell({ title, children }: { title: string; children: ReactNode }) {
  return (
    <RealtimeProvider>
      <div className="flex h-screen bg-bg-primary">
        <Suspense fallback={<div className="w-[230px] shrink-0 border-r border-border bg-bg-secondary" />}>
          <Sidebar />
        </Suspense>
        <div className="flex min-w-0 flex-1 flex-col">
          <TopBar title={title} />
          <main className="flex-1 overflow-y-auto p-6">{children}</main>
        </div>
      </div>
    </RealtimeProvider>
  );
}
