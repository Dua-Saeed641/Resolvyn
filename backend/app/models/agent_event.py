"""AgentEvent — project.md §42. Drives the Activity Timeline (§37)."""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class AgentEvent(SQLModel, table=True):
    event_id: Optional[int] = Field(default=None, primary_key=True)
    ticket_id: str = Field(foreign_key="ticket.ticket_id")
    agent: str
    event_type: str
    description: Optional[str] = None
    status: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
