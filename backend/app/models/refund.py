"""Refund — state of the *simulated* refund API (project.md §38, §70).

Persisted so the same RFD-* id stays consistent everywhere it is shown."""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from app.utils import utcnow


class Refund(SQLModel, table=True):
    refund_id: str = Field(primary_key=True)  # RFD-28192
    order_id: str = Field(index=True)
    transaction_id: str
    amount: int
    status: str = "PROCESSING"  # PROCESSING | COMPLETED | FAILED
    ticket_id: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)
