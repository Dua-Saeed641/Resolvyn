"""Account Agent — profile/settings/access (docs/architecture.md §2.3)."""

from app.agents.base_agent import BaseAgent


class AccountAgent(BaseAgent):
    name = "Account Agent"

    def handle(self, ticket_id: str) -> None:
        raise NotImplementedError("Wire up to app.tools.mock_apis and services.ticket_service.")
