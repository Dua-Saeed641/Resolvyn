/** project.md §37: chronological trace, one of the most important views. */
export interface TimelineEntry {
  timestamp: string;
  label: string;
  detail?: string | null;
}

export function TicketTimeline({ entries }: { entries: TimelineEntry[] }) {
  return (
    <ol className="space-y-3">
      {entries.map((entry, i) => (
        <li key={i} className="flex gap-3 text-sm">
          <span className="w-16 shrink-0 text-text-muted">{entry.timestamp}</span>
          <span className="text-text-body">
            {entry.label}
            {entry.detail ? <span className="text-text-muted"> — {entry.detail}</span> : null}
          </span>
        </li>
      ))}
    </ol>
  );
}
