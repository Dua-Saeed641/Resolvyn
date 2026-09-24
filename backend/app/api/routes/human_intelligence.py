"""Human Intelligence — GUIDE / APPROVE / CORRECT / OVERRIDE / TEACH (docs/context.md)."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.database import engine
from app.human_intelligence import human_service as hs
from app.models import HumanAction
from app.services import ticket_service as tickets

router = APIRouter()


def _wrap(fn):
    try:
        return fn()
    except hs.HumanActionError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


async def _await(coro):
    try:
        return await coro
    except hs.HumanActionError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


class GuideIn(BaseModel):
    ticket_id: str
    text: str


class DecideIn(BaseModel):
    ticket_id: str
    action_id: int
    reason: str | None = None


class CorrectIn(BaseModel):
    ticket_id: str
    correct_action: str
    ai_decision: str | None = None
    reason: str | None = None


class OverrideIn(BaseModel):
    ticket_id: str
    decision: str = ""
    reason: str | None = None


class SayIn(BaseModel):
    ticket_id: str
    text: str


class ResolveIn(BaseModel):
    ticket_id: str
    note: str | None = None


class TeachIn(BaseModel):
    topic: str
    knowledge: str
    department: str = "Other"
    ticket_id: str | None = None


class SuggestIn(BaseModel):
    suggestion: str


@router.get("")
def overview():
    with Session(engine) as s:
        rows = s.exec(select(HumanAction).order_by(HumanAction.human_event_id.desc()).limit(200)).all()
    counts: dict[str, int] = {}
    for r in rows:
        counts[r.event_type] = counts.get(r.event_type, 0) + 1
    return {"total": len(rows), "counts": counts, "actions": [tickets.human_dict(r) for r in rows]}


@router.post("/guide")
def guide(body: GuideIn):
    return _wrap(lambda: hs.guide(body.ticket_id, body.text))


@router.post("/approve")
async def approve(body: DecideIn):
    return await _await(hs.decide_action(body.ticket_id, body.action_id, True, reason=body.reason))


@router.post("/reject")
async def reject(body: DecideIn):
    return await _await(hs.decide_action(body.ticket_id, body.action_id, False, reason=body.reason))


@router.post("/correct")
def correct(body: CorrectIn):
    return _wrap(lambda: hs.correct(body.ticket_id, body.correct_action, body.ai_decision, body.reason))


@router.post("/override")
def override(body: OverrideIn):
    return _wrap(lambda: hs.override(body.ticket_id, body.decision, body.reason))


@router.post("/say")
def say(body: SayIn):
    return _wrap(lambda: hs.say(body.ticket_id, body.text))


@router.post("/resolve")
async def resolve(body: ResolveIn):
    return await _await(hs.resolve_by_human(body.ticket_id, body.note))


@router.post("/teach")
def teach(body: TeachIn):
    return _wrap(lambda: hs.teach(body.topic, body.knowledge, body.department, body.ticket_id))


@router.get("/bugs")
def bugs():
    return tickets.all_bugs()


@router.post("/bugs/{bug_id}/suggest")
async def suggest(bug_id: int, body: SuggestIn):
    return await _await(hs.suggest_for_bug(bug_id, body.suggestion))


@router.get("/approvals")
def approvals():
    return tickets.pending_for_approval()
