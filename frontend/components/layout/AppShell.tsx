"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { Suspense } from "react";

import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import { useLive } from "@/lib/live";
import { cx } from "@/lib/utils";

/** project.md §9: top bar + sidebar + main workspace three-part layout. */
export function AppShell({ title, children }: { title: string; children: ReactNode }) {
  const { toasts, dismissToast } = useLive();
  return (
    <div className="flex h-screen bg-bg-primary">
      <Suspense fallback={<div className="w-[230px] shrink-0 border-r border-border bg-bg-secondary" />}>
        <Sidebar />
      </Suspense>
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar title={title} />
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
      <div className="pointer-events-none fixed bottom-4 right-4 z-50 flex w-80 flex-col gap-2">
        {toasts.map((t) => (
          <div
            key={t.id}
            role="status"
            className={cx(
              "pointer-events-auto animate-fade-in rounded-lg border bg-card-elevated p-3 text-sm",
              t.kind === "bug" ? "border-danger/50" : t.kind === "approval" ? "border-warning/50" : "border-border",
            )}
          >
            <div className="flex items-start justify-between gap-2">
              <p className={cx("font-medium", t.kind === "bug" ? "text-danger" : t.kind === "approval" ? "text-warning" : "text-text-primary")}>
                {t.title}
              </p>
              <button onClick={() => dismissToast(t.id)} className="text-text-muted hover:text-text-primary" aria-label="Dismiss">
                ✕
              </button>
            </div>
            <p className="mt-0.5 text-xs text-text-body">{t.body}</p>
            {t.href && (
              <Link href={t.href} className="mt-2 inline-block text-xs text-text-primary underline underline-offset-2" onClick={() => dismissToast(t.id)}>
                Open ticket
              </Link>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

