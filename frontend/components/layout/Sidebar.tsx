"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { useLive } from "@/lib/live";
import { cx } from "@/lib/utils";

/** project.md §10: sidebar nav, exact grouping and order (+ Memory: docs/architecture.md §2.6). */
const NAV_GROUPS = [
  { items: [{ label: "Overview", href: "/ops/overview" }] },
  {
    items: [
      { label: "Tickets", href: "/ops/tickets" },
      { label: "Agents", href: "/ops/agents" },
      { label: "Customers", href: "/ops/customers" },
      { label: "Knowledge", href: "/ops/knowledge" },
      { label: "Memory", href: "/ops/memory" },
      { label: "Activity", href: "/ops/activity" },
    ],
  },
  {
    heading: "Learning",
    items: [
      { label: "Human Intelligence", href: "/ops/human-intelligence" },
      { label: "Learning Signals", href: "/ops/learning-signals" },
    ],
  },
  {
    heading: "System",
    items: [
      { label: "Analytics", href: "/ops/analytics" },
      { label: "Settings", href: "/ops/settings" },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const { bugs, approvals } = useLive();
  const badge: Record<string, number> = { "/ops/overview": bugs.length + approvals.length, "/ops/tickets": approvals.length };

  return (
    <nav className="flex w-[230px] shrink-0 flex-col border-r border-border bg-bg-secondary px-3 py-4">
      <p className="px-2 text-sm font-semibold tracking-[0.18em] text-text-primary">RESOLVYN</p>
      <p className="px-2 pt-0.5 text-[11px] text-text-secondary">Team console</p>
      <div className="mt-6 flex flex-1 flex-col gap-5 overflow-y-auto">
        {NAV_GROUPS.map((group, i) => (
          <div key={i}>
            {group.heading ? (
              <p className="px-2 pb-1 text-[11px] uppercase tracking-wide text-text-secondary">{group.heading}</p>
            ) : null}
            <div className="flex flex-col gap-0.5">
              {group.items.map((item) => {
                const active = pathname?.startsWith(item.href);
                const n = badge[item.href];
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cx(
                      "flex items-center justify-between rounded px-2 py-1.5 text-sm",
                      active ? "bg-card text-text-primary" : "text-text-body hover:bg-card",
                    )}
                  >
                    {item.label}
                    {n ? (
                      <span className="rounded bg-warning/15 px-1.5 text-[11px] font-medium tabular-nums text-warning" aria-label={`${n} need attention`}>
                        {n}
                      </span>
                    ) : null}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </div>
      <Link href="/" className="mt-3 rounded border border-border px-3 py-2 text-xs text-text-muted hover:bg-card hover:text-text-primary">
        Open the customer side →
      </Link>
    </nav>
  );
}
