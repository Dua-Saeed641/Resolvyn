"""HumanAction — project.md §43. type: GUIDANCE | APPROVAL | CORRECTION |
OVERRIDE | TEACHING (docs/context.md, Human Intelligence Layer)."""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class HumanAction(SQLModel, table=True):
    human_event_id: Optional[int] = Field(default=None, primary_key=True)
    ticket_id: str = Field(foreign_key="ticket.ticket_id")
    event_type: str
    previous_ai_action: Optional[str] = None
    human_action: str
    reason: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
