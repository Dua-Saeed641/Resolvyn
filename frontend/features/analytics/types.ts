/** Mirrors backend/app/api/routes/analytics.py response shape. */
export interface AnalyticsSummary {
  tickets_today: number;
  resolved: number;
  active: number;
  human_interventions: number;
  avg_resolution_seconds: number | null;
  avg_confidence: number | null;
}

export interface ResolutionBreakdown {
  status_distribution: Record<string, number>;
  resolved_count: number;
  avg_resolution_seconds: number | null;
}

export interface AgentPerformance {
  agent: string;
  status: string;
  tickets_handled: number;
  resolved: number;
  avg_confidence: number | null;
}

export interface HumanInterventionBreakdown {
  total: number;
  by_type: Record<string, number>;
}

export interface CustomerOutcome {
  ticket_id: string;
  customer_id: string;
  status: string;
  resolution_time: number | null;
}
