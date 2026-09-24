"""Orchestrator — docs/architecture.md §1 layer 5, §2.3 (Agent Departments).

Routes a ticket to exactly one specialist agent based on judged intent,
manages context handoff, and handles retries (reference architecture,
"Multi-Agent Support System").

Not yet implemented: depends on judgment_service + decision_engine being
wired up first, and on the five agents below existing as callable units.
"""

from app.agents.account_agent import AccountAgent
from app.agents.billing_agent import BillingAgent
from app.agents.logistics_agent import LogisticsAgent
from app.agents.order_agent import OrderAgent
from app.agents.technical_agent import TechnicalAgent

AGENTS_BY_INTENT = {
    "Duplicate Payment": BillingAgent,
    "Refund Status": BillingAgent,
    "Account Access": AccountAgent,
    "Shipping Delay": LogisticsAgent,
    "Order Issue": OrderAgent,
    "Technical Issue": TechnicalAgent,
}


def route(intent: str) -> type:
    """Return the agent class responsible for a given judged intent."""
    return AGENTS_BY_INTENT.get(intent, TechnicalAgent)
