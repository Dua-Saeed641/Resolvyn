"""Shared contract for the five specialist agents (docs/architecture.md §2.3).

Every agent moves through the same state vocabulary wherever it's
displayed (project.md §21) — do not invent per-agent terminology:
IDLE, ANALYZING, RETRIEVING, ACTING, VERIFYING, WAITING, COMPLETED, ERROR.
"""

from abc import ABC, abstractmethod


class BaseAgent(ABC):
    name: str

    @abstractmethod
    def handle(self, ticket_id: str) -> None:
        """Run this agent's workflow for a ticket already routed to it."""
        raise NotImplementedError
