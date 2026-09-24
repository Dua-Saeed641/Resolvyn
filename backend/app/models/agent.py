"""Agent — project.md §19-21. One of the five prototype specialist agents:
Billing, Account, Technical, Order, Logistics (docs/architecture.md §2.3).
"""

from typing import Optional

from sqlmodel import Field, SQLModel


class Agent(SQLModel, table=True):
    name: str = Field(primary_key=True)
    status: str = "IDLE"
    current_ticket_id: Optional[str] = Field(default=None, foreign_key="ticket.ticket_id")
