"""LearningSignal — project.md §44. The recorded artifact that feeds the
Solvable Rulebook (docs/architecture.md §2.6)."""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class LearningSignal(SQLModel, table=True):
    signal_id: Optional[int] = Field(default=None, primary_key=True)
    ticket_id: str = Field(foreign_key="ticket.ticket_id")
    source_event: Optional[str] = None
    signal_type: str
    expected_action: Optional[str] = None
    observed_action: Optional[str] = None
    description: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
