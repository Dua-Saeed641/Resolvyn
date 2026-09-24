import { AppShell } from "@/components/layout/AppShell";
import { KnowledgeSource } from "@/components/knowledge/KnowledgeSource";
import { EmptyState } from "@/components/ui/EmptyState";
import type { KnowledgeDocument } from "@/features/knowledge/types";
import { api } from "@/lib/api";

export default async function KnowledgePage() {
  const documents = await api.get<KnowledgeDocument[]>("/knowledge").catch(() => [] as KnowledgeDocument[]);

  return (
    <AppShell title="Knowledge">
      <div className="rounded border border-border">
        {documents.length === 0 ? (
          <EmptyState title="No knowledge documents" description="No policy or product documents are indexed yet." />
        ) : (
          documents.map((doc) => <KnowledgeSource key={doc.title} doc={doc} />)
        )}
      </div>
    </AppShell>
  );
}
