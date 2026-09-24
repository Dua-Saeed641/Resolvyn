import { KnowledgeSource } from "@/components/knowledge/KnowledgeSource";
import type { TicketKnowledge } from "@/features/tickets/types";

/** spec §16-17: shows the AI consulted real knowledge rather than
 * inventing a decision — or, if nothing matched, the first-time-bug path. */
export function KnowledgePanel({ knowledge }: { knowledge: TicketKnowledge }) {
  if (knowledge.is_first_time_bug) {
    return (
      <div className="rounded border border-warning/30 bg-card p-4 text-sm">
        <p className="text-xs font-medium uppercase tracking-wide text-warning">First-time bug</p>
        <p className="mt-2 text-text-body">This issue does not match a known resolution path.</p>
        <p className="mt-2 text-xs text-text-muted">
          Best available match: {knowledge.documents[0]?.title ?? "none"} (similarity{" "}
          {knowledge.documents[0]?.similarity.toFixed(2) ?? "0.00"}) — below the confidence needed to treat this as
          a known issue. Use Teach to record a resolution for next time.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded border border-border">
      {knowledge.documents.map((doc) => (
        <KnowledgeSource key={doc.title} doc={{ title: doc.title, category: doc.category, referenced_in_tickets: 0 }} similarity={doc.similarity} />
      ))}
    </div>
  );
}
