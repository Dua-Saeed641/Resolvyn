import type { Customer } from "@/features/customers/types";

/** project.md §17, §69: customer context panel. */
export function CustomerCard({ customer }: { customer: Customer }) {
  return (
    <div className="rounded border border-border bg-card p-4">
      <p className="text-sm font-medium text-text-primary">{customer.name}</p>
      <dl className="mt-3 grid grid-cols-2 gap-y-2 text-xs">
        <dt className="text-text-muted">Plan</dt>
        <dd className="text-text-body">{customer.plan}</dd>
        <dt className="text-text-muted">Account age</dt>
        <dd className="text-text-body">{customer.account_age_years} years</dd>
        <dt className="text-text-muted">Recent sentiment</dt>
        <dd className="text-text-body">{customer.recent_sentiment}</dd>
        <dt className="text-text-muted">Open issues</dt>
        <dd className="text-text-body">{customer.open_issues}</dd>
      </dl>
    </div>
  );
}
