"use client";

/** A sorted, single-hue horizontal bar list for an open-ended category (ticket
 *  intents, resolution paths, human-action types — any count that isn't a
 *  small fixed set, so color can't carry identity here; the text label does).
 *  Mark spec: <=10px thick bars, 4px rounded tip, value labeled at the tip
 *  directly (dataviz skill: "Bars -> value at the tip", never hover-only). */
export function RankedBars({ data, max: cap = 8 }: { data: Record<string, number>; max?: number }) {
  const entries = Object.entries(data)
    .sort((a, b) => b[1] - a[1])
    .slice(0, cap);
  if (!entries.length) return <p className="text-sm text-text-muted">No data yet.</p>;
  const peak = Math.max(1, ...entries.map(([, v]) => v));
  return (
    <ul className="space-y-2.5">
      {entries.map(([k, v]) => (
        <li key={k} className="grid grid-cols-[110px_1fr_34px] items-center gap-3">
          <span className="truncate text-[13px] text-text-body">{k}</span>
          <span className="h-2.5 overflow-hidden rounded bg-border" aria-hidden>
            <span className="block h-full rounded-r bg-info" style={{ width: `${Math.max(3, (v / peak) * 100)}%` }} />
          </span>
          <span className="text-right text-[13px] tabular-nums text-text-primary">{v}</span>
        </li>
      ))}
    </ul>
  );
}
