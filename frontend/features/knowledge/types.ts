/** Mirrors backend/app/models/knowledge_document.py. */
export interface KnowledgeDocument {
  title: string;
  category: string;
  used_by_agent?: string | null;
  referenced_in_tickets: number;
}
