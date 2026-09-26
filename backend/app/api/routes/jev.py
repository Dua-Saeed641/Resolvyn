"""Jev lab: run any sentence through Jev and the decision engine exactly as a live call would, and see why.

Read-only: no ticket, no tools, no model call unless the sentence falls in the grey zone of retrieval.
"""

import time
from types import SimpleNamespace

from fastapi import APIRouter
from pydantic import BaseModel

from app.agents.base_agent import TurnContext
from app.decision_engine.decision_engine import decide
from app.judgment import jev
from app.memory.memory_engine import memory
from app.perception import perception_service

router = APIRouter()


class JudgeIn(BaseModel):
    text: str
    previous: str | None = None  # the caller's previous sentence, to see topic carry-over
    expecting_answer: bool = False
    refine: bool = False  # let the fast model help when the rules are unsure (what a live call does)


@router.post("/judge")
async def judge(body: JudgeIn):
    t0 = time.perf_counter()
    enriched = perception_service.enrich(body.text)
    who, why = jev.addressee(enriched["text"], expecting_answer=body.expecting_answer)
    prior = jev.rules_judge(body.previous) if body.previous else None
    j = jev.rules_judge(enriched["text"], prior)
    used_model = False
    if body.refine and jev.is_unsure(enriched["text"], j):
        j = await jev.refine_with_model(enriched["text"], j, [])
        used_model = True
    j.query = jev.write_query(enriched["text"], j)
    jev_ms = (time.perf_counter() - t0) * 1000
    ret = memory.retrieve(j.query, j.department)
    state: dict = {}
    ctx = TurnContext(session=SimpleNamespace(), ticket_id="LAB", text=enriched["text"], entities=enriched["entities"],
                      judgment=j, retrieval=ret, customer=None, state=state, language=enriched["language"])
    d = await decide(ctx) if who != "other" else None
    return {
        "text": enriched["text"],
        "language": enriched["language"],
        "entities": enriched["entities"],
        "addressee": {"who": who, "why": why},
        "judgment": j.public(),
        "dialogue": {"yes": j.yes, "no": j.no, "done": j.done},
        "memory": [{"title": h.title, "kind": h.kind, "score": round(h.score, 2)} for h in ret.top_hits(3)],
        "route": "SIDE_TALK" if d is None else ("SMALL_TALK" if d.small_talk else d.path),
        "reason": why if d is None else d.reason,
        "used_model": used_model,
        "ms": round(jev_ms, 2),
    }
