import { ConfidenceIndicator } from "@/components/ui/ConfidenceIndicator";
import type { Ticket } from "@/features/tickets/types";

/** spec §13-14: AI Understanding + Fast Judgment, merged into one panel —
 * both surface the same structured evidence (intent/sentiment/urgency/
 * confidence/routing). No hidden chain-of-thought, no internal prompts. */
export function AIUnderstanding({ ticket, routingReason }: { ticket: Ticket; routingReason: string | null }) {
  return (
    <div className="flex flex-col gap-4 text-sm">
      <div>
        <p className="text-xs font-medium uppercase tracking-wide text-text-muted">Understanding</p>
        <dl className="mt-2 grid grid-cols-2 gap-y-2 text-xs">
          <dt className="text-text-muted">Intent</dt>
          <dd className="text-text-primary">{ticket.intent ?? "Unclassified"}</dd>
          <dt className="text-text-muted">Sentiment</dt>
          <dd className="text-text-primary">{ticket.sentiment ?? "—"}</dd>
          <dt className="text-text-muted">Urgency</dt>
          <dd className="text-text-primary">{ticket.urgency ?? "—"}</dd>
          <dt className="text-text-muted">Confidence</dt>
          <dd>{ticket.confidence != null ? <ConfidenceIndicator confidence={ticket.confidence} /> : "—"}</dd>
        </dl>
      </div>
      <div>
        <p className="text-xs font-medium uppercase tracking-wide text-text-muted">Routing</p>
        <dl className="mt-2 grid grid-cols-2 gap-y-2 text-xs">
          <dt className="text-text-muted">Assigned agent</dt>
          <dd className="text-text-primary">{ticket.assigned_agent ?? "Unassigned"}</dd>
          <dt className="text-text-muted">Reason</dt>
          <dd className="text-text-primary">{routingReason ?? "—"}</dd>
        </dl>
      </div>
    </div>
  );
}
