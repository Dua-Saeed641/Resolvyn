"""Orchestrator — docs/architecture.md §1 layer 5, §2.3 (Agent Departments).

Routes a conversation to exactly one department agent based on Jev's judgment,
tracks each agent's state for the Agents page, and hands over context when the
department changes mid-call (a caller who starts on billing and ends on account
access is passed to the right desk without repeating themselves).
"""

from sqlmodel import Session, select

from app.agents.account_agent import AccountAgent
from app.agents.base_agent import BaseAgent
from app.agents.billing_agent import BillingAgent
from app.agents.order_agent import OrderAgent
from app.agents.other_agent import OtherAgent
from app.agents.technical_agent import TechnicalAgent
from app.database import engine
from app.models import Agent
from app.services.realtime import hub
from app.vocab import AGENT_STATES

AGENTS: dict[str, BaseAgent] = {
    "Technical": TechnicalAgent(),
    "Billing": BillingAgent(),
    "Account": AccountAgent(),
    "Order": OrderAgent(),
    "Other": OtherAgent(),
}


def route(department: str) -> BaseAgent:
    """Return the agent responsible for a judged department."""
    return AGENTS.get(department, AGENTS["Other"])


def _dict(a: Agent) -> dict:
    return {
        "name": a.name, "status": a.status, "current_ticket_id": a.current_ticket_id,
        "current_operation": a.current_operation, "resolved_today": a.resolved_today,
    }


def set_state(name: str, state: str, ticket_id: str | None = None, operation: str | None = None) -> None:
    assert state in AGENT_STATES, state
    with Session(engine, expire_on_commit=False) as s:
        a = s.get(Agent, name) or Agent(name=name)
        a.status = state
        a.current_ticket_id = ticket_id if state != "IDLE" else None
        a.current_operation = operation if state != "IDLE" else None
        s.add(a)
        s.commit()
    hub.to_ops({"type": "agent_update", "agent": _dict(a)})


def mark_resolved(name: str) -> None:
    with Session(engine, expire_on_commit=False) as s:
        a = s.get(Agent, name)
        if a:
            a.resolved_today += 1
            s.add(a)
            s.commit()
            hub.to_ops({"type": "agent_update", "agent": _dict(a)})


def list_agents() -> list[dict]:
    from app.models import Ticket

    with Session(engine) as s:
        agents = s.exec(select(Agent)).all()
        open_by_agent: dict[str, int] = {}
        conf_by_agent: dict[str, list[int]] = {}
        for t in s.exec(select(Ticket)).all():
            if t.assigned_agent and t.status != "RESOLVED":
                open_by_agent[t.assigned_agent] = open_by_agent.get(t.assigned_agent, 0) + 1
            if t.assigned_agent and t.confidence:
                conf_by_agent.setdefault(t.assigned_agent, []).append(t.confidence)
    out = []
    for a in agents:
        d = _dict(a)
        d["current_tickets"] = open_by_agent.get(a.name, 0)
        c = conf_by_agent.get(a.name, [])
        d["avg_confidence"] = round(sum(c) / len(c)) if c else None
        out.append(d)
    order = list(AGENTS)
    out.sort(key=lambda d: order.index(d["name"]) if d["name"] in order else 99)
    return out


def reset_all() -> None:
    for name in AGENTS:
        set_state(name, "IDLE")
    with Session(engine) as s:
        for a in s.exec(select(Agent)).all():
            a.resolved_today = 0
            s.add(a)
        s.commit()


