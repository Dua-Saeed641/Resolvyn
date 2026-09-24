"""KnowledgeDocument — project.md §30, §60. Common-query memory
(docs/architecture.md §2.6, vector half)."""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class KnowledgeDocument(SQLModel, table=True):
    document_id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    category: str
    used_by_agent: Optional[str] = None
    referenced_in_tickets: int = 0
    last_updated: datetime = Field(default_factory=datetime.utcnow)
