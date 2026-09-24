"""Logistics Agent — shipment delays (docs/architecture.md §2.3;
project.md §19 names this the 5th prototype agent in place of the
reference architecture's "Returns Agent")."""

from app.agents.base_agent import BaseAgent


class LogisticsAgent(BaseAgent):
    name = "Logistics Agent"

    def handle(self, ticket_id: str) -> None:
        raise NotImplementedError("Wire up to app.tools.mock_apis and services.ticket_service.")
