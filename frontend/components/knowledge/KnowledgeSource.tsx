import type { KnowledgeDocument } from "@/features/knowledge/types";

/** project.md §18, §30: clickable retrieved-knowledge source. */
export function KnowledgeSource({ doc, similarity }: { doc: KnowledgeDocument; similarity?: number }) {
  return (
    <div className="flex items-center justify-between border-b border-border px-4 py-2 text-sm">
      <span className="text-text-body">{doc.title}</span>
      {similarity !== undefined ? (
        <span className="text-text-muted">Similarity: {similarity.toFixed(2)}</span>
      ) : (
        <span className="text-text-muted">{doc.referenced_in_tickets} tickets</span>
      )}
    </div>
  );
}
