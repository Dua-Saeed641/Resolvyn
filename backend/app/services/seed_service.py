"""First-run seeding: customers, department agents, historical tickets, SOPs.

The SOPs go through the *same* ingestion pipeline a manager uses from the
Knowledge page — nothing is special-cased. Idempotent.
"""

from datetime import timedelta
from pathlib import Path

from sqlmodel import Session, select

from app.database import engine
from app.memory.ingest import ingest_file
from app.memory.memory_engine import memory
from app.models import Agent, Customer, KnowledgeDocument, Message, Ticket
from app.utils import utcnow
from data.seed_data import AGENTS, CUSTOMERS, HISTORY

SOP_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "sops"


def seed_all() -> dict:
    created = {"customers": 0, "agents": 0, "history": 0, "documents": 0}
    with Session(engine) as s:
        for c in CUSTOMERS:
            if not s.get(Customer, c["customer_id"]):
                s.add(Customer(**c))
                created["customers"] += 1
        for a in AGENTS:
            if not s.get(Agent, a["name"]):
                s.add(Agent(**a))
                created["agents"] += 1
        s.commit()

        have_docs = s.exec(select(KnowledgeDocument)).first() is not None

    if not have_docs and SOP_DIR.exists():
        for f in sorted(SOP_DIR.glob("*.md")):
            ingest_file(f.name, f.read_bytes())
            created["documents"] += 1

    now = utcnow()
    for i, h in enumerate(HISTORY):
        with Session(engine) as s:
            if s.get(Ticket, h["ticket_id"]):
                continue
            when = now - timedelta(days=30 - i * 3)
            cust = s.get(Customer, h["customer_id"])
            s.add(Ticket(
                ticket_id=h["ticket_id"], customer_id=h["customer_id"], customer_name=cust.name if cust else None,
                subject=h["subject"], body=h["subject"], status="RESOLVED", intent=h["intent"],
                assigned_agent=h["department"], confidence=93, channel="Call", handled_by="AI",
                resolution_path="SOLVABLE", one_line_summary=h["subject"], detailed_summary=h["resolution"],
                created_at=when, updated_at=when + timedelta(minutes=4), resolved_at=when + timedelta(minutes=4),
                resolution_time=240, sentiment="Neutral", urgency="Low", priority="MEDIUM",
                jira_key=f"RSV-{h['ticket_id'].split('-')[1]}", jira_status="Done",
            ))
            s.add(Message(ticket_id=h["ticket_id"], sender="CUSTOMER", content=h["subject"], timestamp=when))
            s.add(Message(ticket_id=h["ticket_id"], sender="Resolvyn", content=h["resolution"],
                          timestamp=when + timedelta(minutes=3)))
            s.commit()
        memory.remember_ticket(
            {"ticket_id": h["ticket_id"], "customer_id": h["customer_id"], "subject": h["subject"],
             "intent": h["intent"], "assigned_agent": h["department"]},
            h["resolution"],
        )
        created["history"] += 1

    memory.reload()
    return created
