"""Aggregate metrics for the ops dashboard (project.md §12, §66)."""

from collections import Counter

from sqlmodel import Session, select

from app.database import engine
from app.models import FirstTimeBug, HumanAction, LearningSignal, PendingAction, Ticket
from app.services.sessions import sessions
from app.utils import as_utc


def stats() -> dict:
    with Session(engine) as s:
        tickets = s.exec(select(Ticket)).all()
        humans = s.exec(select(HumanAction)).all()
        bugs = s.exec(select(FirstTimeBug)).all()
        pending = s.exec(select(PendingAction).where(PendingAction.status == "PENDING")).all()
        signals = s.exec(select(LearningSignal)).all()

    total = len(tickets)
    resolved = [t for t in tickets if t.status == "RESOLVED"]
    active = [t for t in tickets if t.status not in ("RESOLVED", "FAILED")]
    waiting = [t for t in tickets if t.status == "WAITING_FOR_HUMAN"]
    ai_resolved = [t for t in resolved if t.handled_by == "AI" and not t.escalated]
    human_touched = [t for t in tickets if t.escalated or t.needs_human or t.handled_by == "HUMAN"]
    times = [t.resolution_time for t in resolved if t.resolution_time]
    confs = [t.confidence for t in tickets if t.confidence]
    intents = Counter(t.intent or "Unclassified" for t in tickets)
    depts = Counter(t.assigned_agent or "Unassigned" for t in tickets)
    by_action = Counter(h.event_type for h in humans)
    paths = Counter(t.resolution_path or "—" for t in tickets)
    return {
        "tickets_total": total,
        "active": len(active),
        "resolved": len(resolved),
        "handled_by_ai": len(ai_resolved),
        "escalated": len([t for t in tickets if t.escalated]),
        "waiting_for_human": len(waiting),
        "human_touched": len(human_touched),
        "first_time_bugs": len(bugs),
        "open_bugs": len([b for b in bugs if b.status == "OPEN"]),
        "pending_approvals": len(pending),
        "live_calls": sessions.active_calls(),
        "avg_resolution_seconds": round(sum(times) / len(times)) if times else None,
        "avg_confidence": round(sum(confs) / len(confs)) if confs else None,
        "human_interventions": len(humans),
        "human_by_type": dict(by_action),
        "learning_signals": len(signals),
        "intents": dict(intents.most_common()),
        "agent_activity": dict(depts.most_common()),
        "paths": dict(paths),
        "ai_resolution_rate": round(100 * len(ai_resolved) / len(resolved)) if resolved else None,
    }


def customers() -> list[dict]:
    from app.models import Customer

    with Session(engine) as s:
        custs = s.exec(select(Customer)).all()
        tickets = s.exec(select(Ticket)).all()
    out = []
    for c in custs:
        mine = [t for t in tickets if t.customer_id == c.customer_id]
        d = c.model_dump()
        d["ticket_count"] = len(mine)
        d["resolved"] = len([t for t in mine if t.status == "RESOLVED"])
        d["open"] = len([t for t in mine if t.status not in ("RESOLVED", "FAILED")])
        last = max((as_utc(t.created_at) for t in mine), default=None)
        d["last_contact"] = last.isoformat() if last else None
        out.append(d)
    return out


