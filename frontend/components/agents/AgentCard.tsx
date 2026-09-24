import { AgentBadge } from "@/components/ui/AgentBadge";
import type { Agent } from "@/features/agents/types";

/** project.md §20: agent roster card. */
export function AgentCard({ agent }: { agent: Agent }) {
  return (
    <div className="rounded border border-border bg-card p-4">
      <AgentBadge name={agent.name} status={agent.status} />
      <p className="mt-2 text-xs text-text-muted">
        {agent.current_ticket_id ? `Working on ${agent.current_ticket_id}` : "No active ticket"}
      </p>
    </div>
  );
}
