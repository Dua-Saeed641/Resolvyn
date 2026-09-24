import { AppShell } from "@/components/layout/AppShell";
import { EmptyState } from "@/components/ui/EmptyState";

/** project.md §28: learning events. Backed by /api/learning-signals once
 * app/learning/learning_service.py is implemented. */
export default function LearningSignalsPage() {
  return (
    <AppShell title="Learning Signals">
      <EmptyState title="No learning signals yet" description="Signals are recorded when a human correction, override, or teaching event occurs." />
    </AppShell>
  );
}
