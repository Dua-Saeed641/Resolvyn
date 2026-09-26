"""First-run seeding: customers, department agents, historical tickets, SOPs.

The SOPs go through the *same* ingestion pipeline a manager uses from the
Knowledge page — nothing is special-cased. Idempotent.
"""

from datetime import timedelta
from pathlib import Path

from sqlmodel import Session, select

from app.config import get_settings
from app.database import engine
from app.memory.ingest import ingest_file
from app.memory.memory_engine import memory
from app.models import Agent, Customer, KnowledgeDocument, Message, Ticket
from app.services import business_data
from app.utils import utcnow
from data.seed_data import AGENTS, CUSTOMERS, HISTORY, LEGACY_CUSTOMER_IDS

SOP_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "sops"


def seed_all() -> dict:
    created = {"customers": 0, "agents": 0, "history": 0, "documents": 0}
    with Session(engine) as s:
        for legacy in LEGACY_CUSTOMER_IDS:  # the demo now has exactly two customers
            row = s.get(Customer, legacy)
            if row:
                s.delete(row)
        for c in CUSTOMERS:
            row = s.get(Customer, c["customer_id"])
            if not row:
                s.add(Customer(**c))
                created["customers"] += 1
            elif row.name != c["name"]:  # an earlier seed used another person for this ID: take over the identity
                for k, v in c.items():
                    setattr(row, k, v)
                s.add(row)
        for pair in (get_settings().customer_emails or "").split(","):
            cid, _, addr = pair.partition(":")
            row = s.get(Customer, cid.strip())
            if row and "@" in addr:
                row.email = addr.strip()
                s.add(row)
        for a in AGENTS:
            if not s.get(Agent, a["name"]):
                s.add(Agent(**a))
                created["agents"] += 1
        s.commit()

        known_sources = {d.source_name for d in s.exec(select(KnowledgeDocument)).all()}

    if SOP_DIR.exists():  # per file, so documents you ingested first never stop the built-in SOPs from loading
        for f in sorted(SOP_DIR.glob("*.md")):
            if f.name in known_sources:
                continue
            ingest_file(f.name, f.read_bytes())
            created["documents"] += 1

    created.update({f"business_{k}": v for k, v in business_data.seed().items()})

    now = utcnow()
    history_count = len(HISTORY)
    for i, h in enumerate(HISTORY):
        with Session(engine) as s:
            existing = s.get(Ticket, h["ticket_id"])
            if existing:
                cust = s.get(Customer, h["customer_id"])
                if cust and (existing.customer_id != h["customer_id"] or existing.customer_name != cust.name):
                    existing.customer_id, existing.customer_name = cust.customer_id, cust.name  # keep old history on the current people
                    s.add(existing)
                    s.commit()
                continue
            # Oldest entry first, newest entry always at least 1 day in the past
            # regardless of how long HISTORY grows (a fixed "30 - i*3" offset put
            # anything past the 10th entry in the future, ahead of live tickets).
            when = now - timedelta(days=history_count - i)
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
