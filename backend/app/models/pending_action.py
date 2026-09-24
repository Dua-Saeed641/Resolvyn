"""PendingAction — an AI-proposed action awaiting the human approval gate
(docs/architecture.md §2.5, "human approval gate"; project.md §24)."""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from app.utils import utcnow


class PendingAction(SQLModel, table=True):
    action_id: Optional[int] = Field(default=None, primary_key=True)
    ticket_id: str = Field(index=True)
    action_type: str  # refund
    summary: str = ""
    params_json: str = "{}"
    risk: str = "Medium"
    policy: str = "Eligible"
    status: str = "PENDING"  # PENDING | APPROVED | REJECTED | EXECUTED | FAILED
    result_json: Optional[str] = None
    decided_by: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)
    decided_at: Optional[datetime] = None
