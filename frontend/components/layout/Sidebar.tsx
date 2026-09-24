"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";

import { cx } from "@/lib/utils";

/** spec §4-5: exact support-operations nav tree. Do not add customer-facing
 * items (My Account, Customer Portal, ...) or unrelated navigation. */
const NAV_GROUPS: {
  heading?: string;
  items: { label: string; href: string; match: (pathname: string, search: string) => boolean }[];
}[] = [
  {
    heading: "Operations",
    items: [
      { label: "Overview", href: "/overview", match: (p) => p === "/overview" },
      { label: "Tickets", href: "/tickets", match: (p) => p.startsWith("/tickets") },
    ],
  },
  {
    heading: "AI Operations",
    items: [
      { label: "Agents", href: "/agents", match: (p) => p.startsWith("/agents") },
      { label: "Routing", href: "/routing", match: (p) => p === "/routing" },
      { label: "Knowledge", href: "/knowledge", match: (p) => p === "/knowledge" },
      { label: "Tool Activity", href: "/tool-activity", match: (p) => p === "/tool-activity" },
    ],
  },
  {
    heading: "Human Intelligence",
    items: [
      {
        label: "Interventions",
        href: "/human-intelligence?tab=interventions",
        match: (p, s) => p === "/human-intelligence" && (s === "" || s === "interventions"),
      },
      {
        label: "Approvals",
        href: "/human-intelligence?tab=approvals",
        match: (p, s) => p === "/human-intelligence" && s === "approvals",
      },
      {
        label: "Corrections",
        href: "/human-intelligence?tab=corrections",
        match: (p, s) => p === "/human-intelligence" && s === "corrections",
      },
    ],
  },
  {
    heading: "Learning",
    items: [
      {
        label: "Learning Signals",
        href: "/learning-signals?view=signals",
        match: (p, s) => p === "/learning-signals" && (s === "" || s === "signals"),
      },
      {
        label: "Prediction Errors",
        href: "/learning-signals?view=prediction-errors",
        match: (p, s) => p === "/learning-signals" && s === "prediction-errors",
      },
      {
        label: "Outcomes",
        href: "/learning-signals?view=outcomes",
        match: (p, s) => p === "/learning-signals" && s === "outcomes",
      },
    ],
  },
  {
    heading: "Analytics",
    items: [
      {
        label: "Resolution",
        href: "/analytics?view=resolution",
        match: (p, s) => p === "/analytics" && (s === "" || s === "resolution"),
      },
      {
        label: "Agent Performance",
        href: "/analytics?view=agent-performance",
        match: (p, s) => p === "/analytics" && s === "agent-performance",
      },
      {
        label: "Human Intervention",
        href: "/analytics?view=human-intervention",
        match: (p, s) => p === "/analytics" && s === "human-intervention",
      },
      {
        label: "Customer Outcomes",
        href: "/analytics?view=customer-outcomes",
        match: (p, s) => p === "/analytics" && s === "customer-outcomes",
      },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname() ?? "";
  const searchParams = useSearchParams();
  const activeParam = searchParams.get("tab") ?? searchParams.get("view") ?? "";

  return (
    <nav className="flex w-[230px] shrink-0 flex-col overflow-y-auto border-r border-border bg-bg-secondary px-3 py-4">
      <p className="px-2 text-sm font-semibold tracking-wide text-text-primary">RESOLVYN</p>

      <div className="mt-6 flex flex-1 flex-col gap-5">
        {NAV_GROUPS.map((group) => (
          <div key={group.heading}>
            <p className="px-2 pb-1 text-[11px] uppercase tracking-wide text-text-secondary">{group.heading}</p>
            <div className="flex flex-col gap-0.5">
              {group.items.map((item) => {
                const active = item.match(pathname, activeParam);
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

      <div className="mt-4 border-t border-border pt-3">
        <Link
          href="/settings"
          className={cx(
            "block rounded px-2 py-1.5 text-sm",
            pathname === "/settings" ? "bg-card text-text-primary" : "text-text-body hover:bg-card"
          )}
        >
          Settings
        </Link>
        <p className="mt-2 px-2 text-xs text-text-muted">Operator 01</p>
      </div>
    </nav>
  );
}
