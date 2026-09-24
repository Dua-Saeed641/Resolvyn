"""The ticket state machine — docs/architecture.md §2.4, §2.7.

This is the ONLY place that writes to Ticket, AgentEvent, ToolCall, or
Agent rows (docs/claude.md, "Ticket state lives in one place"). Every
other service (human_intelligence, agents, demo) calls through here so
the timeline, agent state, and realtime broadcast never drift out of
sync with ticket state.

Pipeline order (docs/context.md, ticket status model):
  NEW -> ANALYZING -> ROUTING -> ACTIVE -> WAITING_FOR_HUMAN -> VERIFYING -> RESOLVED
FAILED is a terminal failure branch reachable from any non-terminal state.
"""

from datetime import datetime, timezone

from sqlmodel import Session, select

from app.models.agent import Agent
from app.models.agent_event import AgentEvent
from app.models.ticket import Ticket
from app.models.tool_call import ToolCall
from app.realtime import manager

STATUS_PIPELINE = [
    "NEW",
    "ANALYZING",
    "ROUTING",
    "ACTIVE",
    "WAITING_FOR_HUMAN",
    "VERIFYING",
    "RESOLVED",
]


def get_ticket(session: Session, ticket_id: str) -> Ticket | None:
    return session.get(Ticket, ticket_id)


def list_tickets(session: Session, status: str | None = None) -> list[Ticket]:
    statement = select(Ticket)
    if status:
        statement = statement.where(Ticket.status == status)
    return list(session.exec(statement).all())


def set_status(
    session: Session,
    ticket_id: str,
    status: str,
    *,
    agent: str = "System",
    description: str | None = None,
) -> Ticket:
    ticket = session.get(Ticket, ticket_id)
    if ticket is None:
        raise ValueError(f"Unknown ticket {ticket_id}")

    ticket.status = status
    ticket.updated_at = datetime.now(timezone.utc)
    if status == "RESOLVED" and ticket.resolution_time is None:
        ticket.resolution_time = int((ticket.updated_at - ticket.created_at).total_seconds())
    session.add(ticket)
    session.commit()
    session.refresh(ticket)

    add_event(session, ticket_id, agent, "STATUS_CHANGED", description or status, status=status)
    manager.broadcast("ticket_updated", ticket.model_dump(mode="json"))
    return ticket


def add_event(
    session: Session,
    ticket_id: str,
    agent: str,
    event_type: str,
    description: str | None = None,
    *,
    status: str | None = None,
) -> AgentEvent:
    event = AgentEvent(
        ticket_id=ticket_id, agent=agent, event_type=event_type, description=description, status=status
    )
    session.add(event)
    session.commit()
    session.refresh(event)
    manager.broadcast("event_created", event.model_dump(mode="json"))
    return event


def set_tool_call(
    session: Session,
    ticket_id: str,
    tool_name: str,
    status: str,
    *,
    request: str | None = None,
    response: str | None = None,
) -> ToolCall:
    existing = session.exec(
        select(ToolCall).where(ToolCall.ticket_id == ticket_id, ToolCall.tool_name == tool_name)
    ).first()

    if existing:
        existing.status = status
        existing.request = request or existing.request
        existing.response = response or existing.response
        existing.timestamp = datetime.now(timezone.utc)
        tool_call = existing
    else:
        tool_call = ToolCall(
            ticket_id=ticket_id, tool_name=tool_name, status=status, request=request, response=response
        )

    session.add(tool_call)
    session.commit()
    session.refresh(tool_call)
    manager.broadcast("tool_call_updated", tool_call.model_dump(mode="json"))
    return tool_call


def list_tool_calls(session: Session, ticket_id: str) -> list[ToolCall]:
    return list(session.exec(select(ToolCall).where(ToolCall.ticket_id == ticket_id)).all())


def list_timeline(session: Session, ticket_id: str) -> list[AgentEvent]:
    return list(
        session.exec(
            select(AgentEvent).where(AgentEvent.ticket_id == ticket_id).order_by(AgentEvent.timestamp)
        ).all()
    )


def set_agent_state(
    session: Session, agent_name: str, status: str, *, current_ticket_id: str | None = None
) -> Agent:
    agent = session.get(Agent, agent_name)
    if agent is None:
        agent = Agent(name=agent_name, status=status, current_ticket_id=current_ticket_id)
    else:
        agent.status = status
        agent.current_ticket_id = current_ticket_id
    session.add(agent)
    session.commit()
    session.refresh(agent)
    manager.broadcast("agent_updated", agent.model_dump(mode="json"))
    return agent
