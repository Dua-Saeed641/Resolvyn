"use client";

import { SENTIMENTS } from "@/lib/constants";

// Sentiment already carries a semantic meaning (good/neutral/bad), so it reuses
// the app's existing status tokens rather than the categorical chart palette.
const TONE: Record<string, string> = {
  Positive: "bg-success",
  Neutral: "bg-text-secondary",
  Frustrated: "bg-warning",
  Angry: "bg-danger",
};

/** One proportional stacked bar across all tickets' sentiment, plus a legend
 *  with counts — a single glance at "is the queue trending upset." Segments
 *  keep the mandated 2px surface gap so touching colors stay distinct. */
export function SentimentBreakdown({ data }: { data: Record<string, number> }) {
  const total = SENTIMENTS.reduce((sum, s) => sum + (data[s] ?? 0), 0);
  if (!total) return <p className="text-sm text-text-muted">No data yet.</p>;
  return (
    <div>
      <div className="flex h-3 gap-0.5 overflow-hidden rounded" role="img" aria-label="Ticket sentiment breakdown">
        {SENTIMENTS.map((s) => {
          const v = data[s] ?? 0;
          if (!v) return null;
          return <span key={s} className={TONE[s]} style={{ width: `${(v / total) * 100}%` }} title={`${s}: ${v}`} />;
        })}
      </div>
      <ul className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1.5">
        {SENTIMENTS.map((s) => (
          <li key={s} className="flex items-center justify-between gap-2 text-[13px]">
            <span className="flex items-center gap-1.5 text-text-body">
              <span className={`h-2 w-2 shrink-0 rounded-full ${TONE[s]}`} aria-hidden />
              {s}
            </span>
            <span className="tabular-nums text-text-primary">{data[s] ?? 0}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
