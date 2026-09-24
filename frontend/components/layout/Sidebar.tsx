"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cx } from "@/lib/utils";

/** project.md §10: sidebar nav, exact grouping and order. */
const NAV_GROUPS = [
  {
    items: [{ label: "Overview", href: "/overview" }],
  },
  {
    items: [
      { label: "Tickets", href: "/tickets" },
      { label: "Agents", href: "/agents" },
      { label: "Customers", href: "/customers" },
      { label: "Knowledge", href: "/knowledge" },
      { label: "Activity", href: "/activity" },
    ],
  },
  {
    heading: "Learning",
    items: [
      { label: "Human Intelligence", href: "/human-intelligence" },
      { label: "Learning Signals", href: "/learning-signals" },
    ],
  },
  {
    heading: "System",
    items: [
      { label: "Analytics", href: "/analytics" },
      { label: "Settings", href: "/settings" },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <nav className="flex w-[230px] shrink-0 flex-col border-r border-border bg-bg-secondary px-3 py-4">
      <p className="px-2 text-sm font-semibold tracking-wide text-text-primary">RESOLVYN</p>
      <div className="mt-6 flex flex-col gap-5">
        {NAV_GROUPS.map((group, i) => (
          <div key={i}>
            {group.heading ? (
              <p className="px-2 pb-1 text-[11px] uppercase tracking-wide text-text-secondary">
                {group.heading}
              </p>
            ) : null}
            <div className="flex flex-col gap-0.5">
              {group.items.map((item) => {
                const active = pathname?.startsWith(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cx(
                      "rounded px-2 py-1.5 text-sm",
                      active ? "bg-card text-text-primary" : "text-text-body hover:bg-card"
                    )}
                  >
                    {item.label}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </nav>
  );
}
