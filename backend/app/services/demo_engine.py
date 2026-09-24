"""Demo Mode — spec §41, §59; project.md §46-48; docs/architecture.md §2.7.

Drives ticket PH-1042 live through the full pipeline using the SAME
service calls a real operator/agent path would use (ticket_engine,
human_intelligence.human_service) — not a canned frontend animation, so
every step is a real, persisted, broadcast state change (spec §54: no
fake features).

RUN DEMO rewinds PH-1042 to NEW and replays the whole journey with short
real delays between steps, ending with an automatic approval performed by
a virtual "Operator (Demo)" through the exact same `human_service.approve`
path a human clicking Approve would take.

RESET DEMO cancels an in-flight run (if any) and restores the ticket to
its default at-rest snapshot (WAITING_FOR_HUMAN, pending refund approval)
as defined in data/seed_data.py.
"""

import asyncio
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, delete, select

from app.database import engine
from app.human_intelligence import human_service
from app.models.agent_event import AgentEvent
from app.models.human_action import HumanAction
from app.models.learning_signal import LearningSignal
from app.models.tool_call import ToolCall
from app.realtime import manager
from app.services import ticket_engine
from app.tools import mock_apis
from data.seed_data import EVENTS, TICKET_AGE, TOOL_CALLS

DEMO_TICKET_ID = "PH-1042"
DEMO_AGENT = "Billing Agent"

_demo_task: asyncio.Task | None = None


def is_running() -> bool:
    return _demo_task is not None and not _demo_task.done()


async def _run(step_delay: float) -> None:
    with Session(engine) as session:
        _clear_ticket_history(session, DEMO_TICKET_ID)

        ticket = ticket_engine.get_ticket(session, DEMO_TICKET_ID)
        ticket.status = "NEW"
        ticket.resolution_time = None
        session.add(ticket)
        session.commit()
        ticket_engine.add_event(session, DEMO_TICKET_ID, "System", "TICKET_CREATED", "Ticket PH-1042 entered queue")
        ticket_engine.set_agent_state(session, DEMO_AGENT, "IDLE", current_ticket_id=None)

    await asyncio.sleep(step_delay)
    with Session(engine) as session:
        ticket_engine.add_event(
            session, DEMO_TICKET_ID, "System", "INTENT_DETECTED", "Duplicate Payment (confidence 96%)"
        )
        ticket_engine.set_status(session, DEMO_TICKET_ID, "ANALYZING", description="Analyzing customer message")

    await asyncio.sleep(step_delay)
    with Session(engine) as session:
        ticket_engine.add_event(
            session, DEMO_TICKET_ID, "Orchestrator", "AGENT_ASSIGNED", "Routed to Billing Agent — payment-related issue"
        )
        ticket_engine.set_status(session, DEMO_TICKET_ID, "ROUTING", description="Routing to specialist agent")
        ticket_engine.set_agent_state(session, DEMO_AGENT, "ANALYZING", current_ticket_id=DEMO_TICKET_ID)

    await asyncio.sleep(step_delay)
    with Session(engine) as session:
        ticket_engine.set_status(session, DEMO_TICKET_ID, "ACTIVE", agent=DEMO_AGENT, description="Billing Agent active")
        ticket_engine.set_agent_state(session, DEMO_AGENT, "RETRIEVING", current_ticket_id=DEMO_TICKET_ID)
        response = mock_apis.get_customer(session, "CUS-20481")
        ticket_engine.set_tool_call(session, DEMO_TICKET_ID, "get_customer", "COMPLETED", request="customer_id=CUS-20481", response=response)

    await asyncio.sleep(step_delay * 0.6)
    with Session(engine) as session:
        response = mock_apis.get_order(session, "ORD-83921")
        ticket_engine.set_tool_call(session, DEMO_TICKET_ID, "get_order", "COMPLETED", request="order_id=ORD-83921", response=response)

    await asyncio.sleep(step_delay * 0.6)
    with Session(engine) as session:
        response = mock_apis.get_payment_transactions("ORD-83921")
        ticket_engine.set_tool_call(
            session, DEMO_TICKET_ID, "get_payment_transactions", "COMPLETED",
            request="order_id=ORD-83921", response=response,
        )
        ticket_engine.add_event(session, DEMO_TICKET_ID, DEMO_AGENT, "KNOWLEDGE_RETRIEVED", "Billing Refund Policy, Payment Processing Guide")

    await asyncio.sleep(step_delay * 0.6)
    with Session(engine) as session:
        ticket_engine.set_agent_state(session, DEMO_AGENT, "ACTING", current_ticket_id=DEMO_TICKET_ID)
        response = mock_apis.check_refund_policy("ORD-83921")
        ticket_engine.set_tool_call(
            session, DEMO_TICKET_ID, "check_refund_policy", "COMPLETED",
            request="order_id=ORD-83921", response=response,
        )

    await asyncio.sleep(step_delay)
    with Session(engine) as session:
        amount = mock_apis.REFUND_AMOUNTS["ORD-83921"]
        ticket_engine.set_tool_call(session, DEMO_TICKET_ID, "issue_refund", "WAITING", request=f"order_id=ORD-83921, amount={amount}")
        ticket_engine.add_event(session, DEMO_TICKET_ID, DEMO_AGENT, "ACTION_PROPOSED", "Issue refund for duplicate transaction")
        ticket_engine.set_status(session, DEMO_TICKET_ID, "WAITING_FOR_HUMAN", agent=DEMO_AGENT, description="Refund action requires human approval")
        ticket_engine.set_agent_state(session, DEMO_AGENT, "WAITING", current_ticket_id=DEMO_TICKET_ID)

    await asyncio.sleep(step_delay * 1.5)
    with Session(engine) as session:
        human_service.approve(session, DEMO_TICKET_ID, operator="Operator (Demo)")
        # Billing Agent still has PH-1044 outstanding — hand its attention back there.
        ticket_engine.set_agent_state(session, DEMO_AGENT, "WAITING", current_ticket_id="PH-1044")


def start_demo(step_delay: float = 1.4) -> dict:
    """Called from a sync FastAPI route running in a worker thread — the
    task must be created ON the event loop thread, so this hands the
    actual `create_task` call to that thread via `call_soon_threadsafe`
    rather than calling `asyncio.get_event_loop()` here (which raises:
    there is no event loop bound to a worker thread).
    """
    global _demo_task
    if is_running():
        return {"status": "already_running"}
    if manager.loop is None:
        raise RuntimeError("Server not fully started yet — try again in a moment.")

    def _create_task() -> None:
        global _demo_task
        _demo_task = manager.loop.create_task(_run(step_delay))

    manager.loop.call_soon_threadsafe(_create_task)
    return {"status": "started", "ticket_id": DEMO_TICKET_ID}


def _clear_ticket_history(session: Session, ticket_id: str) -> None:
    session.exec(delete(AgentEvent).where(AgentEvent.ticket_id == ticket_id))
    session.exec(delete(ToolCall).where(ToolCall.ticket_id == ticket_id))
    session.exec(delete(HumanAction).where(HumanAction.ticket_id == ticket_id))
    session.exec(delete(LearningSignal).where(LearningSignal.ticket_id == ticket_id))
    session.commit()


def reset_demo() -> dict:
    global _demo_task
    if _demo_task is not None and not _demo_task.done() and manager.loop is not None:
        manager.loop.call_soon_threadsafe(_demo_task.cancel)
    _demo_task = None

    with Session(engine) as session:
        _clear_ticket_history(session, DEMO_TICKET_ID)

        ticket = ticket_engine.get_ticket(session, DEMO_TICKET_ID)
        now = datetime.now(timezone.utc)
        created_min, updated_min = TICKET_AGE[DEMO_TICKET_ID]
        ticket.status = "WAITING_FOR_HUMAN"
        ticket.confidence = 96
        ticket.resolution_time = None
        ticket.assigned_agent = DEMO_AGENT
        ticket.created_at = now - timedelta(minutes=created_min)
        ticket.updated_at = now - timedelta(minutes=updated_min)
        session.add(ticket)
        session.commit()

        for agent, event_type, description, status, minutes_ago in EVENTS[DEMO_TICKET_ID]:
            session.add(
                AgentEvent(
                    ticket_id=DEMO_TICKET_ID, agent=agent, event_type=event_type, description=description,
                    status=status, timestamp=now - timedelta(minutes=minutes_ago),
                )
            )
        for tool_name, status, request, response, minutes_ago in TOOL_CALLS[DEMO_TICKET_ID]:
            session.add(
                ToolCall(
                    ticket_id=DEMO_TICKET_ID, tool_name=tool_name, status=status, request=request,
                    response=response, timestamp=now - timedelta(minutes=minutes_ago),
                )
            )
        session.commit()

        ticket_engine.set_agent_state(session, DEMO_AGENT, "WAITING", current_ticket_id=DEMO_TICKET_ID)

    return {"status": "reset", "ticket_id": DEMO_TICKET_ID}
