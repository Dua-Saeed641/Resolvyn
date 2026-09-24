/** Mirrors backend/app/models/customer.py. */
export interface Customer {
  customer_id: string;
  name: string;
  plan: string;
  account_age_years: number;
  recent_sentiment: string;
  open_issues: number;
}
