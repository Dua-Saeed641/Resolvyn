"""Message — project.md §41. sender: CUSTOMER | Resolvyn | HUMAN | SYSTEM.

kind separates real conversation from `side_talk` (the caller talking to
someone else, docs/architecture.md §2.1) so it never pollutes the ticket body.
"""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from app.utils import utcnow


class Message(SQLModel, table=True):
    message_id: Optional[int] = Field(default=None, primary_key=True)
    ticket_id: str = Field(foreign_key="ticket.ticket_id", index=True)
    sender: str
    content: str
    kind: str = "speech"  # speech | chat | side_talk | system
    timestamp: datetime = Field(default_factory=utcnow)
