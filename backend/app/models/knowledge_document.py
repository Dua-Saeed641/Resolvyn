"""KnowledgeDocument — project.md §30, §60. One row per ingested source
(SOP / business logic / product DB). Its chunks live in MemoryChunk
(docs/architecture.md §2.6, vector half)."""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from app.utils import utcnow


class KnowledgeDocument(SQLModel, table=True):
    document_id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    category: str = "Policies"
    kind: str = "sop"  # sop | business_logic | product_db
    department: Optional[str] = None  # dominant department (auto-classified)
    source_name: Optional[str] = None
    chunk_count: int = 0
    used_by_agent: Optional[str] = None
    referenced_in_tickets: int = 0
    last_updated: datetime = Field(default_factory=utcnow)
