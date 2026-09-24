"""HumanAction — project.md §43. type: GUIDANCE | APPROVAL | CORRECTION |
OVERRIDE | TEACHING (docs/context.md, Human Intelligence Layer)."""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from app.utils import utcnow


class HumanAction(SQLModel, table=True):
    human_event_id: Optional[int] = Field(default=None, primary_key=True)
    ticket_id: Optional[str] = Field(default=None, index=True)  # None for org-wide Teach actions
    event_type: str
    previous_ai_action: Optional[str] = None
    human_action: str
    reason: Optional[str] = None
    operator: str = "Operator 01"
    timestamp: datetime = Field(default_factory=utcnow)
