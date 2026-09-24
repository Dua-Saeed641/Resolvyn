"""Owns ticket state (docs/architecture.md §2.4, §3 mapping table; docs/claude.md).

This is the only module allowed to read/write the `ticket`, `message` and
`agentevent` tables — routes and other services go through it. Every mutation
is pushed in real time to both audiences (docs/architecture.md §2.4):
  * ops side  → everything (summaries, confidence, timeline, tools…)
  * caller    → customer-safe view only ("one line summary — team side only")
"""


from sqlmodel import Session, select

from app.database import engine
from app.models import (
    AgentEvent,
    FirstTimeBug,
    HumanAction,
    Message,
    PendingAction,
    Ticket,
    ToolCall,
)
from app.services.realtime import hub
from app.utils import iso, jdump, jload, utcnow
from app.vocab import TICKET_STATUSES, confidence_label

FIRST_LIVE_TICKET = 1042

FRIENDLY_STATUS = {
    "NEW": "Ticket created",
    "ANALYZING": "Understanding your request",
    "ROUTING": "Finding the right team",
    "ACTIVE": "In progress",
    "WAITING_FOR_HUMAN": "With our team",
    "VERIFYING": "Verifying the result",
    "RESOLVED": "Resolved",
    "FAILED": "Needs attention",
}


# ── serialisation ────────────────────────────────────────────────────────────


def _ticket_dict(t: Ticket) -> dict:
    d = t.model_dump()
    for k in ("created_at", "updated_at", "resolved_at"):
        d[k] = iso(getattr(t, k))
    d["confidence_label"] = confidence_label(t.confidence)
    d["knowledge"] = jload(t.knowledge_json, [])
    d["guidance"] = jload(t.guidance_json, [])
    d.pop("knowledge_json", None)
    d.pop("guidance_json", None)
    return d


def summary(t: Ticket) -> dict:
    """Row for the ticket list (no big text fields)."""
    d = _ticket_dict(t)
    for k in ("context_doc", "detailed_summary", "deep_summary", "body"):
        d.pop(k, None)
    return d


def _event_dict(e: AgentEvent) -> dict:
    meta = jload(e.meta_json, {}) or {}
    return {
        "event_id": e.event_id,
        "ticket_id": e.ticket_id,
        "agent": e.agent,
        "event_type": e.event_type,
        "description": e.description,
        "status": e.status,
        "meta": meta,
        "timestamp": iso(e.timestamp),
    }


def _message_dict(m: Message) -> dict:
    return {
        "message_id": m.message_id,
        "ticket_id": m.ticket_id,
        "sender": m.sender,
        "content": m.content,
        "kind": m.kind,
        "timestamp": iso(m.timestamp),
    }


def _tool_dict(c: ToolCall) -> dict:
    return {
        "tool_call_id": c.tool_call_id,
        "ticket_id": c.ticket_id,
        "tool_name": c.tool_name,
        "status": c.status,
        "request": jload(c.request, {}),
        "response": jload(c.response, None),
        "timestamp": iso(c.timestamp),
    }


def _pending_dict(p: PendingAction) -> dict:
    return {
        "action_id": p.action_id,
        "ticket_id": p.ticket_id,
        "action_type": p.action_type,
        "summary": p.summary,
        "params": jload(p.params_json, {}),
        "risk": p.risk,
        "policy": p.policy,
        "status": p.status,
        "result": jload(p.result_json, None),
        "decided_by": p.decided_by,
        "created_at": iso(p.created_at),
        "decided_at": iso(p.decided_at),
    }


def _human_dict(h: HumanAction) -> dict:
    return {
        "human_event_id": h.human_event_id,
        "ticket_id": h.ticket_id,
        "event_type": h.event_type,
        "previous_ai_action": h.previous_ai_action,
        "human_action": h.human_action,
        "reason": h.reason,
        "operator": h.operator,
        "timestamp": iso(h.timestamp),
    }


def _bug_dict(b: FirstTimeBug) -> dict:
    return {
        "bug_id": b.bug_id,
        "ticket_id": b.ticket_id,
        "title": b.title,
        "detail": b.detail,
        "department": b.department,
        "status": b.status,
        "suggestion": b.suggestion,
        "suggested_by": b.suggested_by,
        "created_at": iso(b.created_at),
        "resolved_at": iso(b.resolved_at),
    }


def detail(ticket_id: str) -> dict | None:
    """Everything the team side needs to open a ticket and understand the AI's progress."""
    with Session(engine) as s:
        t = s.get(Ticket, ticket_id)
        if t is None:
            return None
        msgs = s.exec(select(Message).where(Message.ticket_id == ticket_id).order_by(Message.message_id)).all()
        evs = s.exec(select(AgentEvent).where(AgentEvent.ticket_id == ticket_id).order_by(AgentEvent.event_id)).all()
        tools = s.exec(select(ToolCall).where(ToolCall.ticket_id == ticket_id).order_by(ToolCall.tool_call_id)).all()
        pend = s.exec(select(PendingAction).where(PendingAction.ticket_id == ticket_id).order_by(PendingAction.action_id)).all()
        hum = s.exec(select(HumanAction).where(HumanAction.ticket_id == ticket_id).order_by(HumanAction.human_event_id)).all()
        bugs = s.exec(select(FirstTimeBug).where(FirstTimeBug.ticket_id == ticket_id)).all()
        d = _ticket_dict(t)
        d["messages"] = [_message_dict(m) for m in msgs]
        d["events"] = [_event_dict(e) for e in evs]
        d["tool_calls"] = [_tool_dict(c) for c in tools]
        d["pending_actions"] = [_pending_dict(p) for p in pend]
        d["human_actions"] = [_human_dict(h) for h in hum]
        d["bugs"] = [_bug_dict(b) for b in bugs]
        return d


# What the caller sees: friendly status, department, timeline, refund state —
# never confidence, the internal summary, or tool payloads.
_PUBLIC_EVENTS = {
    "TICKET_CREATED", "AGENT_ASSIGNED", "ACTION_PROPOSED", "ACTION_APPROVED", "ACTION_EXECUTED",
    "ACTION_VERIFIED", "ESCALATED", "FIRST_TIME_BUG_FLAGGED", "TICKET_RESOLVED", "HUMAN_TAKEOVER",
}


def customer_view(ticket_id: str) -> dict | None:
    with Session(engine) as s:
        t = s.get(Ticket, ticket_id)
        if t is None:
            return None
        evs = s.exec(select(AgentEvent).where(AgentEvent.ticket_id == ticket_id).order_by(AgentEvent.event_id)).all()
        pend = s.exec(select(PendingAction).where(PendingAction.ticket_id == ticket_id).order_by(PendingAction.action_id)).all()
        timeline = []
        for e in evs:
            meta = jload(e.meta_json, {}) or {}
            text = meta.get("public")
            if e.event_type in _PUBLIC_EVENTS and text:
                timeline.append({"time": iso(e.timestamp), "text": text})
        actions = []
        for p in pend:
            actions.append({
                "type": p.action_type,
                "summary": p.summary,
                "status": p.status,
                "result": jload(p.result_json, None),
            })
        return {
            "ticket_id": t.ticket_id,
            "subject": t.subject,
            "status": t.status,
            "status_label": FRIENDLY_STATUS.get(t.status, t.status),
            "department": t.assigned_agent,
            "customer_name": t.customer_name,
            "priority": t.priority,
            "escalated": t.escalated,
            "needs_human": t.needs_human,
            "call_active": t.call_active,
            "created_at": iso(t.created_at),
            "updated_at": iso(t.updated_at),
            "timeline": timeline,
            "actions": actions,
        }


def _emit_ticket(t: Ticket) -> None:
    hub.to_ops({"type": "ticket_update", "ticket": summary(t)})
    hub.to_session(t.session_id, {"type": "ticket", "ticket": customer_view(t.ticket_id)})


# ── queries ──────────────────────────────────────────────────────────────────


def get(ticket_id: str) -> Ticket | None:
    with Session(engine) as s:
        return s.get(Ticket, ticket_id)


def list_tickets(status: str | None = None, agent: str | None = None, limit: int = 200) -> list[dict]:
    with Session(engine) as s:
        q = select(Ticket).order_by(Ticket.created_at.desc()).limit(limit)
        rows = s.exec(q).all()
    out = [summary(t) for t in rows]
    if status:
        out = [t for t in out if t["status"] == status]
    if agent:
        out = [t for t in out if t["assigned_agent"] == agent]
    return out


def find_by_session(session_id: str) -> Ticket | None:
    with Session(engine) as s:
        return s.exec(select(Ticket).where(Ticket.session_id == session_id).order_by(Ticket.created_at.desc())).first()


def tickets_for_customer(customer_id: str) -> list[dict]:
    with Session(engine) as s:
        rows = s.exec(
            select(Ticket).where(Ticket.customer_id == customer_id).order_by(Ticket.created_at.desc())
        ).all()
    return [summary(t) for t in rows]


def active_call_count() -> int:
    with Session(engine) as s:
        return len(s.exec(select(Ticket).where(Ticket.call_active == True)).all())  # noqa: E712


# ── mutations ────────────────────────────────────────────────────────────────


def _next_id(s: Session) -> str:
    nums = []
    for tid in s.exec(select(Ticket.ticket_id)).all():
        try:
            nums.append(int(tid.split("-")[1]))
        except Exception:
            continue
    nxt = max([n for n in nums if n >= FIRST_LIVE_TICKET - 1] + [FIRST_LIVE_TICKET - 1]) + 1
    return f"PH-{nxt}"


def create(
    session_id: str,
    *,
    channel: str = "Call",
    customer_id: str | None = None,
    customer_name: str | None = None,
    language: str = "en",
) -> Ticket:
    with Session(engine, expire_on_commit=False) as s:
        t = Ticket(
            ticket_id=_next_id(s),
            customer_id=customer_id,
            customer_name=customer_name,
            channel=channel,
            language=language,
            session_id=session_id,
            call_active=channel == "Call",
        )
        s.add(t)
        s.commit()
    add_event(
        t.ticket_id, "Resolvyn", "TICKET_CREATED", f"{channel} started — ticket {t.ticket_id} created",
        status="NEW", public="Ticket created",
    )
    _emit_ticket(t)
    return t


def update(ticket_id: str, **fields) -> Ticket:
    if "status" in fields and fields["status"] not in TICKET_STATUSES:
        raise ValueError(f"invalid ticket status {fields['status']!r} (docs/claude.md vocabulary)")
    for k in ("knowledge", "guidance"):
        if k in fields:
            fields[f"{k}_json"] = jdump(fields.pop(k))
    with Session(engine, expire_on_commit=False) as s:
        t = s.get(Ticket, ticket_id)
        if t is None:
            raise KeyError(ticket_id)
        for k, v in fields.items():
            setattr(t, k, v)
        t.updated_at = utcnow()
        if fields.get("status") == "RESOLVED" and t.resolved_at is None:
            t.resolved_at = utcnow()
            t.resolution_time = int((t.resolved_at - t.created_at).total_seconds())
            t.call_active = False
        s.add(t)
        s.commit()
    _emit_ticket(t)
    return t


def add_message(ticket_id: str, sender: str, content: str, kind: str = "speech") -> dict:
    with Session(engine, expire_on_commit=False) as s:
        m = Message(ticket_id=ticket_id, sender=sender, content=content, kind=kind)
        s.add(m)
        s.commit()
    d = _message_dict(m)
    t = get(ticket_id)
    hub.to_ops({"type": "message", "message": d})
    if t:
        hub.to_session(t.session_id, {"type": "transcript", "message": d})
    return d


def add_event(
    ticket_id: str,
    agent: str,
    event_type: str,
    description: str,
    *,
    status: str | None = None,
    meta: dict | None = None,
    public: str | None = None,
) -> dict:
    meta = dict(meta or {})
    if public:
        meta["public"] = public
    with Session(engine, expire_on_commit=False) as s:
        e = AgentEvent(
            ticket_id=ticket_id,
            agent=agent,
            event_type=event_type,
            description=description,
            status=status,
            meta_json=jdump(meta) if meta else None,
        )
        s.add(e)
        s.commit()
    d = _event_dict(e)
    hub.to_ops({"type": "event", "event": d})
    if public:
        t = get(ticket_id)
        if t:
            hub.to_session(t.session_id, {"type": "ticket", "ticket": customer_view(ticket_id)})
    return d


def messages(ticket_id: str, *, include_side_talk: bool = False) -> list[dict]:
    with Session(engine) as s:
        rows = s.exec(select(Message).where(Message.ticket_id == ticket_id).order_by(Message.message_id)).all()
    return [_message_dict(m) for m in rows if include_side_talk or m.kind != "side_talk"]


def events(ticket_id: str) -> list[dict]:
    with Session(engine) as s:
        rows = s.exec(select(AgentEvent).where(AgentEvent.ticket_id == ticket_id).order_by(AgentEvent.event_id)).all()
    return [_event_dict(e) for e in rows]


def recent_events(limit: int = 100) -> list[dict]:
    with Session(engine) as s:
        rows = s.exec(select(AgentEvent).order_by(AgentEvent.event_id.desc()).limit(limit)).all()
    return [_event_dict(e) for e in rows]


def pending_for_approval() -> list[dict]:
    with Session(engine) as s:
        rows = s.exec(select(PendingAction).where(PendingAction.status == "PENDING")).all()
    return [_pending_dict(p) for p in rows]


def open_bugs() -> list[dict]:
    with Session(engine) as s:
        rows = s.exec(select(FirstTimeBug).where(FirstTimeBug.status == "OPEN")).all()
    return [_bug_dict(b) for b in rows]


def all_bugs() -> list[dict]:
    with Session(engine) as s:
        rows = s.exec(select(FirstTimeBug).order_by(FirstTimeBug.bug_id.desc())).all()
    return [_bug_dict(b) for b in rows]


# Re-exported so other modules don't need to reach into private helpers.
pending_dict = _pending_dict
bug_dict = _bug_dict
human_dict = _human_dict
tool_dict = _tool_dict
event_dict = _event_dict
message_dict = _message_dict
