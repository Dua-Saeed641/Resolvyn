import { AppShell } from "@/components/layout/AppShell";
import { EmptyState } from "@/components/ui/EmptyState";

/** project.md §22, §79: human intervention log and summary. Backed by
 * /api/human-intelligence once human_intelligence/human_service.py is
 * implemented (docs/architecture.md §2.5). */
export default function HumanIntelligencePage() {
  return (
    <AppShell title="Human Intelligence">
      <EmptyState title="No interventions yet" description="Guide, approval, correction, override, and teach events will appear here." />
    </AppShell>
  );
}
