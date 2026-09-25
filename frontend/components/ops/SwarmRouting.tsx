import type { AgentEvent } from "@/features/types";
import { Pill } from "@/components/ui/StatusBadge";
import { cx } from "@/lib/utils";

interface SwarmCandidate {
  agent: string;
  activation_score: number;
  matched_intent: string | null;
  reason: string;
}

interface SwarmMeta {
  candidates: SwarmCandidate[];
  winner: string;
  runner_up: string | null;
  activation_gap: number;
  ambiguous: boolean;
  routing_reason: string;
  failed_experts: string[];
}

function latestSwarmMeta(events: AgentEvent[]): SwarmMeta | null {
  for (let i = events.length - 1; i >= 0; i--) {
    const meta = events[i].meta?.swarm as SwarmMeta | undefined;
    if (meta) return meta;
  }
  return null;
}

/** The fruit-fly-inspired mixture-of-experts routing stage's result (agents/swarm_router.py,
 *  docs/swarm-router.md) — a bio-inspired software routing mechanism, not a biological simulation.
 *  Simple bars + labels only, per project.md §57: color is never the only signal. */
export function SwarmRouting({ events }: { events: AgentEvent[] }) {
  const meta = latestSwarmMeta(events);
  if (!meta) return <p className="text-sm text-text-muted">No routing decision recorded yet.</p>;

  const ranked = [...meta.candidates].sort((a, b) => b.activation_score - a.activation_score);

  return (
    <div className="space-y-3">
      {meta.ambiguous && (
        <Pill tone="warning">Ambiguous — narrowly led by {meta.winner} over {meta.runner_up ?? "no runner-up"}</Pill>
      )}
      <ul className="space-y-2">
        {ranked.map((c) => {
          const selected = c.agent === meta.winner && !meta.ambiguous;
          const failed = meta.failed_experts?.includes(c.agent);
          return (
            <li key={c.agent}>
              <div className="flex items-center justify-between text-[13px]">
                <span className={cx("font-medium", selected ? "text-text-primary" : "text-text-body")}>
                  {c.agent} Agent
                </span>
                <span className="flex items-center gap-2">
                  <span className="tabular-nums text-text-muted">{c.activation_score.toFixed(2)}</span>
                  {selected && <Pill tone="success">SELECTED</Pill>}
                  {failed && <Pill tone="danger">FAILED</Pill>}
                </span>
              </div>
              <div className="mt-1 h-1.5 w-full overflow-hidden rounded bg-border">
                <div
                  className={cx("h-full rounded", selected ? "bg-success" : failed ? "bg-danger" : "bg-text-muted")}
                  style={{ width: `${Math.round(c.activation_score * 100)}%` }}
                />
              </div>
            </li>
          );
        })}
      </ul>
      <p className="border-t border-border pt-2 text-xs text-text-muted">{meta.routing_reason}</p>
    </div>
  );
}
