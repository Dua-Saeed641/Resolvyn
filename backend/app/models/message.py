"""Message — project.md §41. sender: CUSTOMER | Resolvyn | HUMAN."""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Message(SQLModel, table=True):
    message_id: Optional[int] = Field(default=None, primary_key=True)
    ticket_id: str = Field(foreign_key="ticket.ticket_id")
    sender: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
