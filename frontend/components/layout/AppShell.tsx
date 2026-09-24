import type { ReactNode } from "react";

import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";

/** project.md §9: top bar + sidebar + main workspace three-part layout. */
export function AppShell({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="flex h-screen bg-bg-primary">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar title={title} />
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  );
}
