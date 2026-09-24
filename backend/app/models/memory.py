"""Memory system tables — docs/architecture.md §2.6 / memory-rulebook-detail.png.

Two memories, each with a vector half and a knowledge-graph half:
  * store="common"          Business logic / SOPs / Product DB / past solved queries
  * store="first_time_bug"  first-time bugs (issues with no precedent)
MemoryChunk is the vector half; KgNode/KgEdge are the knowledge-graph half.
RulebookEntry is the Solvable Rulebook that human suggestions extend.
"""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from app.utils import utcnow


class MemoryChunk(SQLModel, table=True):
    chunk_id: Optional[int] = Field(default=None, primary_key=True)
    store: str = Field(default="common", index=True)  # common | first_time_bug
    kind: str = "sop"  # sop | business_logic | product_db | past_query | bug | rule
    department: str = "Other"  # Technical | Billing | Account | Order | Other
    title: str = ""
    text: str = ""
    document_id: Optional[int] = Field(default=None, index=True)
    ref_ticket_id: Optional[str] = Field(default=None, index=True)
    source: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)


class KgNode(SQLModel, table=True):
    node_id: str = Field(primary_key=True)  # "<type>:<slug>"
    type: str  # concept | department | ticket | customer | rule | document | bug
    label: str
    weight: int = 1
    store: str = "common"


class KgEdge(SQLModel, table=True):
    edge_id: Optional[int] = Field(default=None, primary_key=True)
    src: str = Field(index=True)
    dst: str = Field(index=True)
    relation: str
    weight: int = 1


class RulebookEntry(SQLModel, table=True):
    rule_id: Optional[int] = Field(default=None, primary_key=True)
    topic: str
    knowledge: str
    department: str = "Other"
    source: str = "human_teach"  # human_teach | first_time_bug_suggestion | human_correction | seed
    ticket_id: Optional[str] = None
    active: bool = True
    created_at: datetime = Field(default_factory=utcnow)


class FirstTimeBug(SQLModel, table=True):
    bug_id: Optional[int] = Field(default=None, primary_key=True)
    ticket_id: str = Field(index=True)
    title: str
    detail: str = ""
    department: str = "Technical"
    status: str = "OPEN"  # OPEN | SUGGESTED
    suggestion: Optional[str] = None
    suggested_by: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)
    resolved_at: Optional[datetime] = None
