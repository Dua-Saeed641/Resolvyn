"use client";

import {
  Activity, BarChart3, BookOpen, Bot, Brain, Database, GraduationCap, LayoutDashboard, Mail, Network, Settings, ShieldCheck, Ticket, Users,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { Logo } from "@/components/brand/Logo";
import { useLive } from "@/lib/live";
import { cn } from "@/lib/utils";

type Item = { label: string; href: string; icon: LucideIcon };
const NAV_GROUPS: { heading?: string; items: Item[] }[] = [
  { items: [{ label: "Overview", href: "/ops/overview", icon: LayoutDashboard }] },
  {
    heading: "Operations",
    items: [
      { label: "Tickets", href: "/ops/tickets", icon: Ticket },
      { label: "Agents", href: "/ops/agents", icon: Bot },
      { label: "Routing", href: "/ops/routing", icon: Network },
      { label: "Customers", href: "/ops/customers", icon: Users },
      { label: "Emails", href: "/ops/emails", icon: Mail },
      { label: "Activity", href: "/ops/activity", icon: Activity },
    ],
  },
  {
    heading: "Knowledge",
    items: [
      { label: "Knowledge", href: "/ops/knowledge", icon: BookOpen },
      { label: "Business data", href: "/ops/business-data", icon: Database },
      { label: "Memory", href: "/ops/memory", icon: Brain },
    ],
  },
  {
    heading: "Learning",
    items: [
      { label: "Human intelligence", href: "/ops/human-intelligence", icon: ShieldCheck },
      { label: "Learning signals", href: "/ops/learning-signals", icon: GraduationCap },
    ],
  },
  {
    heading: "System",
    items: [
      { label: "Analytics", href: "/ops/analytics", icon: BarChart3 },
      { label: "Settings", href: "/ops/settings", icon: Settings },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const { bugs, approvals } = useLive();
  const badge: Record<string, number> = { "/ops/overview": bugs.length + approvals.length, "/ops/tickets": approvals.length };

  return (
    <nav className="flex w-[240px] shrink-0 flex-col border-r bg-card px-3 py-4">
      <Link href="/ops/overview" className="px-2" aria-label="Resolvyn team console">
        <Logo size={34} subtitle="Team console" />
      </Link>
      <div className="mt-6 flex flex-1 flex-col gap-5 overflow-y-auto">
        {NAV_GROUPS.map((group, i) => (
          <div key={i}>
            {group.heading ? <p className="px-2 pb-1.5 text-[11px] font-medium uppercase tracking-wider text-text-secondary">{group.heading}</p> : null}
            <div className="flex flex-col gap-0.5">
              {group.items.map((item) => {
                const active = pathname?.startsWith(item.href);
                const n = badge[item.href];
                const Icon = item.icon;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      "flex items-center gap-2.5 rounded-md px-2 py-1.5 text-sm transition-colors",
                      active ? "bg-accent font-medium text-foreground" : "text-muted-foreground hover:bg-accent/60 hover:text-foreground",
                    )}
                  >
                    <Icon className="h-4 w-4 shrink-0" />
                    <span className="flex-1 truncate">{item.label}</span>
                    {n ? (
                      <span className="rounded-full bg-warning/15 px-1.5 text-[11px] font-medium tabular-nums text-warning" aria-label={`${n} need attention`}>
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
      <Link href="/" className="mt-3 rounded-md border px-3 py-2 text-center text-xs font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground">
        Open the customer side
      </Link>
    </nav>
  );
}
