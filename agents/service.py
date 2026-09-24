"""ResolvynOrchestrator — the reusable graph/service factory (spec §47).

One compiled graph, one checkpointer, reused across every ticket — never
rebuilt per request. `thread_id` (LangGraph's own concept) is simply the
ticket_id: one durable, resumable conversation-with-the-graph per ticket.
"""

import asyncio
from pathlib import Path

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Command

from agents.graph import build_graph
from agents.state import ResolvynState, new_state, public_state

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True)
DEFAULT_DB_PATH = DATA_DIR / "checkpoints.db"


class OrchestrationError(ValueError):
    pass


class ResolvynOrchestrator:
    """Owns the compiled graph + checkpointer for one process (or one test).

    Use as an async context manager:

        async with ResolvynOrchestrator() as orch:
            result = await orch.start("PH-1042", "I was charged twice...")
    """

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        self._db_path = str(db_path)
        self._saver_cm = None
        self._checkpointer = None
        self._graph = None
        self._lock = asyncio.Lock()

    async def __aenter__(self) -> "ResolvynOrchestrator":
        self._saver_cm = AsyncSqliteSaver.from_conn_string(self._db_path)
        self._checkpointer = await self._saver_cm.__aenter__()
        self._graph = build_graph(self._checkpointer)
        return self

    async def __aexit__(self, *exc) -> None:
        if self._saver_cm is not None:
            await self._saver_cm.__aexit__(*exc)
        self._saver_cm = self._checkpointer = self._graph = None

    def _config(self, ticket_id: str) -> dict:
        return {"configurable": {"thread_id": ticket_id}}

    async def start(self, ticket_id: str, text: str, *, channel: str = "Ticket", language: str = "en") -> dict:
        """Begin a fresh orchestration run for this ticket (spec §7).

        Idempotent in practice: LangGraph keys checkpoints by (thread_id,
        checkpoint), so re-`start`ing a ticket that already has a completed
        thread starts a new checkpoint chain on the same thread rather than
        silently reusing stale state — callers that want to resume a
        *paused* run should call `resume`, not `start` again.
        """
        state = new_state(ticket_id, text, channel=channel, language=language)
        async with self._lock:
            result = await self._graph.ainvoke(state, config=self._config(ticket_id))
        return self._shape(ticket_id, result)

    async def resume(self, ticket_id: str, action: dict) -> dict:
        """Continue a paused run after a human action (spec §7, §15-16).

        `action` is `{"action": "APPROVE"|"GUIDE"|"CORRECT"|"OVERRIDE"|"TEACH", ...}`
        — see `agents/nodes.py::human_gate` for the exact per-action shape.
        """
        snapshot = await self._graph.aget_state(self._config(ticket_id))
        if not snapshot.values:
            raise OrchestrationError(f"no orchestration run found for ticket {ticket_id}")
        if not snapshot.next:  # empty `next` = the thread already ran to completion
            raise OrchestrationError(f"ticket {ticket_id} is not waiting for a human action")
        async with self._lock:
            result = await self._graph.ainvoke(Command(resume=action), config=self._config(ticket_id))
        return self._shape(ticket_id, result)

    async def get_raw_state(self, ticket_id: str) -> ResolvynState | None:
        snapshot = await self._graph.aget_state(self._config(ticket_id))
        return snapshot.values or None

    async def get_state(self, ticket_id: str) -> dict | None:
        """Domain state for the dashboard/API — never framework internals (spec §26, §50)."""
        snapshot = await self._graph.aget_state(self._config(ticket_id))
        if not snapshot.values:
            return None
        state = public_state(snapshot.values)
        state["paused"] = bool(snapshot.next)
        state["pending_human_gate"] = snapshot.interrupts[0].value if snapshot.interrupts else None
        return state

    def _shape(self, ticket_id: str, result: dict) -> dict:
        out = public_state(result)
        out["ticket_id"] = ticket_id
        out["paused"] = "__interrupt__" in result
        if out["paused"]:
            out["pending_human_gate"] = result["__interrupt__"][0].value
        return out
