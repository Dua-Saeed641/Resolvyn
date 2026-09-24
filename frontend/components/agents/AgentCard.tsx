import Link from "next/link";

import { AgentBadge } from "@/components/ui/AgentBadge";
import type { Agent } from "@/features/agents/types";

/** spec §20: agent roster card — clicking reveals current tasks (§21). */
export function AgentCard({ agent }: { agent: Agent }) {
  return (
    <Link href={`/agents/${encodeURIComponent(agent.name)}`} className="block rounded border border-border bg-card p-4 hover:border-text-muted">
      <AgentBadge name={agent.name} status={agent.status} />
      <p className="mt-2 text-xs text-text-muted">
        {agent.current_ticket_id ? `Working on ${agent.current_ticket_id}` : "No active ticket"}
      </p>
    </Link>
  );
}
