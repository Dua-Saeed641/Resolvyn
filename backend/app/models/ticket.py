"""Ticket — project.md §33-34, §40.

Status must be one of exactly: NEW, ANALYZING, ROUTING, ACTIVE,
WAITING_FOR_HUMAN, VERIFYING, RESOLVED, FAILED (docs/claude.md, vocab rules).
"""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Ticket(SQLModel, table=True):
    ticket_id: str = Field(primary_key=True)
    customer_id: str = Field(foreign_key="customer.customer_id")
    subject: str
    status: str = "NEW"
    intent: Optional[str] = None
    sentiment: Optional[str] = None
    urgency: Optional[str] = None
    priority: str = "MEDIUM"
    assigned_agent: Optional[str] = None
    confidence: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    resolution_time: Optional[int] = None
