"""Agent — project.md §19-21. The department agents chosen "on the basis of
the user query" (docs/architecture.md §2.3): Technical, Billing, Account,
Order, Other."""

from typing import Optional

from sqlmodel import Field, SQLModel


class Agent(SQLModel, table=True):
    name: str = Field(primary_key=True)
    status: str = "IDLE"
    current_ticket_id: Optional[str] = None
    current_operation: Optional[str] = None
    resolved_today: int = 0
