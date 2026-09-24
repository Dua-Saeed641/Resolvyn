"""LearningSignal — project.md §44. The recorded artifact that feeds the
Solvable Rulebook (docs/architecture.md §2.6). A learning-event concept, not
a trained RL model (project.md §29)."""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from app.utils import utcnow


class LearningSignal(SQLModel, table=True):
    signal_id: Optional[int] = Field(default=None, primary_key=True)
    ticket_id: str = Field(foreign_key="ticket.ticket_id", index=True)
    source_event: Optional[str] = None
    signal_type: str
    expected_action: Optional[str] = None
    observed_action: Optional[str] = None
    description: Optional[str] = None
    timestamp: datetime = Field(default_factory=utcnow)
