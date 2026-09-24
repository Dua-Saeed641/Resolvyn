"""Orchestration API — spec §28.

Mounted into the real backend by ONE bridge file
(`backend/app/api/routes/orchestration.py`) plus one `include_router` line in
`backend/app/api/router.py` — see agents/README.md §5. This module itself
never imports anything from `backend/app/api`; the dependency runs the other
way, keeping `agents/` genuinely standalone (it can be tested, and even run,
without the backend process at all — see agents/tests).

The frontend never talks to LangGraph — only to these plain REST endpoints,
returning plain JSON (spec §27: "the frontend consumes Resolvyn domain
events/state," never framework internals).
"""

import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agents.service import OrchestrationError, ResolvynOrchestrator

router = APIRouter()

_orchestrator: ResolvynOrchestrator | None = None
_init_lock = asyncio.Lock()


async def get_orchestrator() -> ResolvynOrchestrator:
    """Lazy singleton: one compiled graph + one open checkpointer connection
    for the process's lifetime (spec §47: never rebuild the graph per route)."""
    global _orchestrator
    if _orchestrator is None:
        async with _init_lock:
            if _orchestrator is None:  # re-check inside the lock
                orch = ResolvynOrchestrator()
                await orch.__aenter__()
                _orchestrator = orch
    return _orchestrator


class ProcessRequest(BaseModel):
    text: str | None = None  # defaults to the ticket's own subject/body if omitted
    channel: str = "Ticket"


@router.post("/tickets/{ticket_id}/process")
async def process_ticket(ticket_id: str, body: ProcessRequest):
    """spec §7: the orchestration entry point — the backend runs the graph."""
    from app.services import ticket_service as tickets  # local import: agents._bootstrap must run first

    ticket = tickets.get(ticket_id)
    if ticket is None:
        raise HTTPException(404, "Ticket not found")
    text = body.text or ticket.body or ticket.subject
    orch = await get_orchestrator()
    try:
        return await orch.start(ticket_id, text, channel=body.channel, language=ticket.language)
    except Exception as e:  # noqa: BLE001 — spec §31: never swallow, always surface as a structured failure
        tickets.add_event(ticket_id, "Orchestrator", "ERROR", f"Orchestration failed: {type(e).__name__}: {e}", status="FAILED")
        raise HTTPException(500, f"orchestration failed: {type(e).__name__}: {e}") from e


class ResumeRequest(BaseModel):
    action: str  # GUIDE | APPROVE | CORRECT | OVERRIDE | TEACH
    operator: str = "Operator 01"
    guidance: str | None = None
    approve: bool | None = None
    correction: str | None = None
    decision: str | None = None
    topic: str | None = None
    knowledge: str | None = None
    reason: str | None = None


@router.post("/tickets/{ticket_id}/resume")
async def resume_ticket(ticket_id: str, body: ResumeRequest):
    """spec §15-16: resume a paused graph after a human action."""
    action = body.action.upper()
    if action not in {"GUIDE", "APPROVE", "CORRECT", "OVERRIDE", "TEACH"}:
        raise HTTPException(400, f"unknown action {body.action!r}")
    payload = {k: v for k, v in body.model_dump().items() if v is not None}
    payload["action"] = action
    orch = await get_orchestrator()
    try:
        return await orch.resume(ticket_id, payload)
    except OrchestrationError as e:
        raise HTTPException(409, str(e)) from e
    except Exception as e:  # noqa: BLE001
        from app.services import ticket_service as tickets

        tickets.add_event(ticket_id, "Orchestrator", "ERROR", f"Resume failed: {type(e).__name__}: {e}", status="FAILED")
        raise HTTPException(500, f"resume failed: {type(e).__name__}: {e}") from e


@router.get("/tickets/{ticket_id}/orchestration")
async def get_orchestration_state(ticket_id: str):
    """spec §28: read-only orchestration state for the dashboard."""
    orch = await get_orchestrator()
    state = await orch.get_state(ticket_id)
    if state is None:
        raise HTTPException(404, "No orchestration run for this ticket")
    return state
