"""Ticket — project.md §33-34, §40 plus the context-engine fields from
docs/architecture.md §2.5 (ticket id, customer name, body, AI confidence,
one-line summary for the team side).

Status must be one of exactly: NEW, ANALYZING, ROUTING, ACTIVE,
WAITING_FOR_HUMAN, VERIFYING, RESOLVED, FAILED (docs/claude.md, vocab rules).
"""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from app.utils import utcnow


class Ticket(SQLModel, table=True):
    ticket_id: str = Field(primary_key=True)
    customer_id: Optional[str] = Field(default=None, foreign_key="customer.customer_id")
    customer_name: Optional[str] = None
    subject: str = "New conversation"
    body: str = ""  # what the caller said, extracted live (side-talk excluded)
    status: str = "NEW"
    intent: Optional[str] = None
    sentiment: Optional[str] = None
    urgency: Optional[str] = None
    priority: str = "MEDIUM"
    assigned_agent: Optional[str] = None  # Technical | Billing | Account | Order | Other
    confidence: Optional[int] = None
    order_id: Optional[str] = None
    channel: str = "Call"  # Call | Text | Email | Audio
    language: str = "en"
    session_id: Optional[str] = None
    call_active: bool = False

    # Resolution path (docs/architecture.md §2.2)
    resolution_path: Optional[str] = None  # INSTANT | SOLVABLE | ACTION | FIRST_TIME_BUG | ESCALATED
    handled_by: str = "AI"  # AI | HUMAN
    escalated: bool = False
    escalation_reason: Optional[str] = None
    is_first_time_bug: bool = False
    needs_human: bool = False

    # Context engine output (team side)
    one_line_summary: Optional[str] = None
    detailed_summary: Optional[str] = None
    deep_summary: Optional[str] = None  # written by the 27B deep tier after the call
    next_step: Optional[str] = None
    context_doc: Optional[str] = None  # simulated Confluence context doc (markdown)
    jira_key: Optional[str] = None  # simulated Jira/Zoho sync
    jira_status: Optional[str] = None
    assignee: Optional[str] = None  # person on the resolving team
    knowledge_json: Optional[str] = None  # sources retrieved for this ticket (title, store, score)
    guidance_json: Optional[str] = None  # human guidance/suggestions injected into the live AI

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    resolved_at: Optional[datetime] = None
    resolution_time: Optional[int] = None  # seconds
