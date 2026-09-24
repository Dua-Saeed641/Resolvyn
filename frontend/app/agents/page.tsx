import { AgentCard } from "@/components/agents/AgentCard";
import { AppShell } from "@/components/layout/AppShell";
import { EmptyState } from "@/components/ui/EmptyState";
import type { Agent } from "@/features/agents/types";
import { api } from "@/lib/api";

/** spec §20: agent roster — five specialists, no fabricated benchmarks. */
export default async function AgentsPage() {
  const agents = await api.get<Agent[]>("/agents").catch(() => [] as Agent[]);

  return (
    <AppShell title="Agents">
      {agents.length === 0 ? (
        <EmptyState title="No agents" description="No specialist agents are configured yet." />
      ) : (
        <div className="grid grid-cols-3 gap-3">
          {agents.map((agent) => (
            <AgentCard key={agent.name} agent={agent} />
          ))}
        </div>
      )}
    </AppShell>
  );
}
