"""Demo Mode (project.md §46-48): a scripted *caller* through the real pipeline.

Nothing on the AI side is faked: the scripted customer sends the same
utterances a person would say, and Resolvyn perceives, judges, retrieves,
decides, calls tools and speaks exactly as it does on a live call. The only
scripted part is the caller — and, in auto mode, the human at the approval gate.
"""

import asyncio

from sqlmodel import Session

from app.agents import orchestrator
from app.database import engine
from app.human_intelligence import human_service
from app.models import Customer
from app.services import conversation
from app.services import ticket_service as tickets
from app.services.realtime import hub
from app.services.sessions import sessions
from app.tools import mock_apis
from data.seed_data import DEMO_SCENARIOS

SCRIPTED_SUGGESTION = (
    "That purple flashing light with code P-77 means the firmware update failed halfway. "
    "Hold the power button for fifteen seconds to force recovery mode, then plug in the charger and wait for the light to turn white."
)

_running: dict[str, asyncio.Task] = {}


def scenarios() -> list[dict]:
    return [{"id": k, "title": v["title"], "customer_id": v["customer_id"], "turns": len(v["turns"])} for k, v in DEMO_SCENARIOS.items()]


async def _wait_agent_done(q: asyncio.Queue, timeout: float = 90.0) -> None:
    async def _loop():
        while True:
            ev = await q.get()
            if ev.get("type") in ("agent_done", "side_talk"):
                return
    await asyncio.wait_for(_loop(), timeout)


async def _auto_human(ticket_id: str, scenario: str) -> None:
    """In auto mode a scripted operator answers the gates so the run completes hands-free."""
    for _ in range(60):
        await asyncio.sleep(1.5)
        for a in tickets.pending_for_approval():
            if a["ticket_id"] == ticket_id:
                await asyncio.sleep(3)
                try:
                    await human_service.decide_action(ticket_id, a["action_id"], True, operator="Operator 01 (demo)",
                                                      reason="Duplicate transaction verified")
                except human_service.HumanActionError:
                    pass
                return
        if scenario == "first_time_bug":
            for b in tickets.open_bugs():
                if b["ticket_id"] == ticket_id:
                    await asyncio.sleep(6)
                    try:
                        await human_service.suggest_for_bug(b["bug_id"], SCRIPTED_SUGGESTION, operator="Operator 01 (demo)")
                    except human_service.HumanActionError:
                        pass
                    return


async def _run(scenario_id: str, auto_human: bool) -> None:
    sc = DEMO_SCENARIOS[scenario_id]
    with Session(engine) as s:
        cust = s.get(Customer, sc["customer_id"])
    session = sessions.create(channel="Call", customer=cust.model_dump() if cust else None)
    q = hub.subscribe_session(session.session_id)
    hub.to_ops({"type": "demo", "state": "running", "scenario": scenario_id})
    helper = None
    try:
        await conversation.start(session)
        await _wait_agent_done(q, 10)
        if auto_human:
            helper = asyncio.create_task(_auto_human(session.ticket_id, scenario_id))
        for line in sc["turns"]:
            await asyncio.sleep(2.2)  # a person takes a moment before answering
            conversation.submit(session, line)
            try:
                await _wait_agent_done(q)
                gate = session.state.get("awaiting")
                if gate in ("approval", "bug_followup"):
                    # a human is needed: wait for the gate to clear, then for the
                    # AI's proactive reply that follows (approval / suggestion)
                    for _ in range(240):
                        if session.state.get("awaiting") != gate:
                            break
                        await asyncio.sleep(1)
                    await _wait_agent_done(q, 60)
            except asyncio.TimeoutError:
                break
        await asyncio.sleep(4)
        await conversation.end_call(session, "demo finished")
    finally:
        hub.unsubscribe_session(session.session_id, q)
        if helper:
            helper.cancel()
        hub.to_ops({"type": "demo", "state": "finished", "scenario": scenario_id, "ticket_id": session.ticket_id})
        _running.pop(scenario_id, None)


def run(scenario_id: str, auto_human: bool = True) -> dict:
    if scenario_id not in DEMO_SCENARIOS:
        raise KeyError(scenario_id)
    if scenario_id in _running and not _running[scenario_id].done():
        return {"started": False, "reason": "already running"}
    _running[scenario_id] = asyncio.create_task(_run(scenario_id, auto_human))
    return {"started": True, "scenario": scenario_id}


def reset() -> None:
    """RESET DEMO: wipe demo tickets and mutable simulated state; keep seeds + knowledge."""
    from sqlmodel import delete

    from app.memory import kg  # noqa: F401
    from app.models import (
        AgentEvent, FirstTimeBug, HumanAction, KgEdge, KgNode, LearningSignal, MemoryChunk, Message, PendingAction,
        Refund, RulebookEntry, Ticket, ToolCall,
    )
    from app.memory.memory_engine import memory

    for t in _running.values():
        t.cancel()
    _running.clear()
    sessions.clear()
    with Session(engine) as s:
        live = [t.ticket_id for t in s.exec(__import__("sqlmodel").select(Ticket)).all() if int(t.ticket_id.split("-")[1]) >= 1042]
        if live:
            for model in (AgentEvent, Message, ToolCall, HumanAction, LearningSignal, PendingAction):
                s.exec(delete(model).where(model.ticket_id.in_(live)))
            s.exec(delete(FirstTimeBug))
            s.exec(delete(Ticket).where(Ticket.ticket_id.in_(live)))
        s.exec(delete(Refund))
        s.exec(delete(RulebookEntry))
        s.exec(delete(MemoryChunk).where(MemoryChunk.kind.in_(["rule", "bug"])))
        s.exec(delete(MemoryChunk).where(MemoryChunk.kind == "past_query", MemoryChunk.ref_ticket_id.in_(live or [""])))
        # graph nodes tied to removed tickets/bugs/rules
        s.exec(delete(KgEdge).where(KgEdge.src.like("bug:%") | KgEdge.src.like("rule:%")))
        s.exec(delete(KgNode).where(KgNode.type.in_(["bug", "rule"])))
        for tid in live:
            nid = f"ticket:{tid.lower()}"
            s.exec(delete(KgEdge).where((KgEdge.src == nid) | (KgEdge.dst == nid)))
            s.exec(delete(KgNode).where(KgNode.node_id == nid))
        s.commit()
    mock_apis.reset_state()
    memory.reload()
    orchestrator.reset_all()
    hub.to_ops({"type": "reset"})
