import { AppShell } from "@/components/layout/AppShell";
import { EmptyState } from "@/components/ui/EmptyState";

export default function SettingsPage() {
  return (
    <AppShell title="Settings">
      <EmptyState title="Nothing to configure yet" description="Prototype settings will appear here." />
    </AppShell>
  );
}
