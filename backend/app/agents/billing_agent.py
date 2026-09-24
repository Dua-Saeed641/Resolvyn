"""Billing Agent — invoices/payments/refunds (docs/architecture.md §2.3).

Reference trace for this agent (docs/architecture.md §2.7, hero ticket
PH-1042): get_customer -> get_order -> get_payment_transactions ->
check_refund_policy -> issue_refund -> verify_refund (project.md §18).
"""

from app.agents.base_agent import BaseAgent


class BillingAgent(BaseAgent):
    name = "Billing Agent"

    def handle(self, ticket_id: str) -> None:
        raise NotImplementedError("Wire up to app.tools.mock_apis and services.ticket_service.")
