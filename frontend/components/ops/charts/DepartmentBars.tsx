"use client";

import { DEPARTMENTS } from "@/lib/constants";

// Fixed slot order — must match tailwind.config.ts's `chart.1..5` comment and
// lib/constants.ts's DEPARTMENTS exactly. Never reassign a department's slot;
// the colorblind-safety validation (dataviz skill) is for THIS order.
const SLOT = ["bg-chart-1", "bg-chart-2", "bg-chart-3", "bg-chart-4", "bg-chart-5"];

/** Ticket volume by department — a small, fixed categorical set, so (unlike
 *  RankedBars) color-coding carries real identity here. Every department is
 *  shown even at zero, always in the same order, so the chart's shape doesn't
 *  reshuffle as counts change. Each bar carries its own direct text label, so
 *  no separate legend box is needed (dataviz skill: a legend exists so the
 *  reader never relies on color-matching alone — here every bar is already
 *  self-labeled, not just color-keyed to a distant swatch). */
export function DepartmentBars({ data }: { data: Record<string, number> }) {
  const peak = Math.max(1, ...DEPARTMENTS.map((d) => data[d] ?? 0));
  return (
    <ul className="space-y-2.5">
      {DEPARTMENTS.map((d, i) => {
        const v = data[d] ?? 0;
        return (
          <li key={d} className="grid grid-cols-[80px_1fr_34px] items-center gap-3">
            <span className="flex items-center gap-1.5 truncate text-[13px] text-text-body">
              <span className={`h-2 w-2 shrink-0 rounded-full ${SLOT[i]}`} aria-hidden />
              {d}
            </span>
            <span className="h-2.5 overflow-hidden rounded bg-border" aria-hidden>
              <span className={`block h-full rounded-r ${SLOT[i]}`} style={{ width: `${Math.max(v ? 3 : 0, (v / peak) * 100)}%` }} />
            </span>
            <span className="text-right text-[13px] tabular-nums text-text-primary">{v}</span>
          </li>
        );
      })}
    </ul>
  );
}
