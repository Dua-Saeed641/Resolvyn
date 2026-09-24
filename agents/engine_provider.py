"""The Epsilon/engine integration boundary (spec §32-33).

Lovekesh owns the actual intelligence engine (`backend/app/llm/` — "the
only door to a model," per docs/claude.md — plus Jev's model-assisted
refinement in `backend/app/judgment/jev.py`). This module does not
reimplement, wrap a second time, or invent a contract for any of that; it
is the one seam the orchestration graph calls through, so that if the
Epsilon contract changes, this file is the only thing that needs to.

Every method here is deterministic by default and safe with no model
configured — the same guarantee `backend/app/judgment/jev.py` and
`backend/app/decision_engine/decision_engine.py` already give (verified by
`backend/tests`, which run with `ENGINE_ENABLED=false`). `RealEngineProvider`
exists as the documented extension point for when a model-assisted path is
wanted; it currently delegates to the exact same deterministic functions,
because that is what the rest of the pipeline already does when Jev decides
a judgment is ambiguous enough to consult the model
(`jev.is_unsure` / `jev.refine_with_model`).
"""

from abc import ABC, abstractmethod

from app.agents.base_agent import TurnContext
from app.decision_engine.decision_engine import Decision, decide
from app.judgment import jev
from app.memory.memory_engine import Retrieval, memory
from app.perception import perception_service


class EngineProvider(ABC):
    """classify / judge / reason / plan / generate_response — spec §32.

    `plan` and `generate_response` are deliberately NOT here: those are the
    specialist agent's and the response node's job respectively (spec §35's
    responsibility separation — the engine provider judges and reasons about
    the *understanding* of a ticket; it does not perform domain actions or
    write customer-facing copy).
    """

    @abstractmethod
    def perceive(self, raw_text: str, channel: str) -> dict:
        """Clean-up, language, entity extraction (spec §8)."""

    @abstractmethod
    def judge(self, text: str, *, plan: str | None = None) -> jev.Judgment:
        """Intent, sentiment, urgency, department, confidence (spec §9)."""

    @abstractmethod
    def write_query(self, text: str, judgment: jev.Judgment, *, subject: str | None = None) -> str:
        """The retrieval query Jev derives from the judged text (spec §10)."""

    @abstractmethod
    def retrieve(self, query: str, department: str | None, *, exclude_ticket: str | None = None) -> Retrieval:
        """Common + first-time-bug memory retrieval (spec §10, §17)."""

    @abstractmethod
    async def reason(self, ctx: TurnContext) -> Decision:
        """Analyze → Plan → Evaluate → Choose a resolution path (spec §11)."""


class DeterministicEngineProvider(EngineProvider):
    """No model required. This is what `pytest` and CI exercise, and what the
    graph falls back to whenever `RealEngineProvider`'s underlying model is
    not ready — mirroring exactly how `backend/app/services/conversation.py`
    already behaves (`if not llm.ready("fast"): return _fallback(...)`).
    """

    def perceive(self, raw_text: str, channel: str) -> dict:
        return perception_service.enrich(raw_text, channel)

    def judge(self, text: str, *, plan: str | None = None) -> jev.Judgment:
        return jev.rules_judge(text, plan=plan)

    def write_query(self, text: str, judgment: jev.Judgment, *, subject: str | None = None) -> str:
        return jev.write_query(text, judgment, subject=subject)

    def retrieve(self, query: str, department: str | None, *, exclude_ticket: str | None = None) -> Retrieval:
        return memory.retrieve(query, department, exclude_ticket=exclude_ticket)

    async def reason(self, ctx: TurnContext) -> Decision:
        return await decide(ctx)  # already has its own model-optional grounding check (jev.grounded)


class RealEngineProvider(DeterministicEngineProvider):
    """Placeholder for a model-assisted path (spec §33: "RealEngineProvider").

    Intentionally identical to the deterministic provider today: the actual
    model-assisted refinement (`jev.refine_with_model`, `jev.grounded`) is
    already invoked from inside the functions this delegates to, gated on
    `backend/app/llm.llm.ready(...)`. There is no separate Epsilon contract
    to invent here (spec §32: "do not invent endpoints for the Epsilon
    repository") — when Lovekesh's engine changes, the change lands in
    `backend/app/llm/` and this class needs no edits.
    """


def judgment_dict(j: jev.Judgment) -> dict:
    return j.public()


def judgment_from_dict(d: dict) -> jev.Judgment:
    d = dict(d)
    d.pop("extras", None)
    return jev.Judgment(**d)
