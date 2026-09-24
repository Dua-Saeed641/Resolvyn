"""Routing decisions — spec §22. Derived from real ticket + orchestrator
data rather than a separate fabricated log, so it can never drift from
what actually happened (docs/claude.md, "traceable actions").
"""

from sqlmodel import Session, select

from app.agents.orchestrator import route
from app.models.ticket import Ticket


def list_routing_decisions(session: Session) -> list[dict]:
    tickets = session.exec(select(Ticket).order_by(Ticket.updated_at.desc())).all()
    decisions = []
    for ticket in tickets:
        if not ticket.intent or not ticket.assigned_agent:
            continue
        _, reason = route(ticket.intent)
        decisions.append(
            {
                "ticket_id": ticket.ticket_id,
                "issue": ticket.subject,
                "intent": ticket.intent,
                "destination": ticket.assigned_agent,
                "confidence": ticket.confidence,
                "reason": reason,
                "timestamp": ticket.updated_at,
            }
        )
    return decisions
