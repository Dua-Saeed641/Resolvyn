"""ToolCall — records every simulated enterprise API call (project.md §18, §38)."""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class ToolCall(SQLModel, table=True):
    tool_call_id: Optional[int] = Field(default=None, primary_key=True)
    ticket_id: str = Field(foreign_key="ticket.ticket_id")
    tool_name: str
    status: str = "NOT_STARTED"
    request: Optional[str] = None
    response: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
