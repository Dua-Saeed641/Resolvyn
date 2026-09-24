"""AgentEvent — project.md §42. Drives the Activity Timeline (§37)."""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from app.utils import utcnow


class AgentEvent(SQLModel, table=True):
    event_id: Optional[int] = Field(default=None, primary_key=True)
    ticket_id: str = Field(foreign_key="ticket.ticket_id", index=True)
    agent: str
    event_type: str
    description: Optional[str] = None
    status: Optional[str] = None
    meta_json: Optional[str] = None  # structured details (e.g. knowledge sources + scores)
    timestamp: datetime = Field(default_factory=utcnow)
