/** Mirrors backend/app/api/routes/analytics.py response shape. */
export interface AnalyticsSummary {
  tickets_today: number;
  resolved: number;
  active: number;
  human_interventions: number;
}
