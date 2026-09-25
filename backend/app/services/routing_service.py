"""Routing decisions — spec §22, §40. Read straight from the AGENT_ASSIGNED
event agents/nodes.py::route_agent already writes (with its swarm-routing
meta payload, agents/swarm_router.py) rather than a second, potentially
drifting copy of the same decision (docs/claude.md, "traceable actions").
"""

from sqlmodel import Session, select

from app.models.agent_event import AgentEvent
from app.models.ticket import Ticket
from app.utils import iso, jload


def list_routing_decisions(session: Session, limit: int = 100) -> list[dict]:
    tickets = session.exec(select(Ticket).order_by(Ticket.updated_at.desc()).limit(limit)).all()
    decisions = []
    for ticket in tickets:
        latest = session.exec(
            select(AgentEvent)
            .where(AgentEvent.ticket_id == ticket.ticket_id, AgentEvent.event_type == "AGENT_ASSIGNED")
            .order_by(AgentEvent.event_id.desc())
            .limit(1)
        ).first()
        if latest is None:
            continue
        swarm = (jload(latest.meta_json, {}) or {}).get("swarm")
        if not swarm:
            continue  # a ticket routed before this feature existed — no swarm data to show, not an error
        decisions.append({
            "ticket_id": ticket.ticket_id,
            "issue": ticket.subject,
            "intent": ticket.intent,
            "candidates": swarm.get("candidates", []),
            "winner": swarm.get("winner"),
            "runner_up": swarm.get("runner_up"),
            "activation_gap": swarm.get("activation_gap"),
            "ambiguous": swarm.get("ambiguous"),
            "reason": swarm.get("routing_reason"),
            "timestamp": iso(latest.timestamp),
        })
    return decisions
