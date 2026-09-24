import type { AgentState } from "@/lib/constants";

/** Mirrors backend/app/models/agent.py. */
export interface Agent {
  name: string;
  status: AgentState;
  current_ticket_id?: string | null;
}
