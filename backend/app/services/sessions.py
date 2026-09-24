"""Live call sessions: the in-memory state of one conversation.

A session outlives the WebSocket (docs/architecture.md §2.4): if the caller hangs
up while a refund is waiting for approval, the session stays so the agent can
still execute the approved refund and update the caller's ticket.
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.judgment.jev import Judgment
from app.utils import utcnow


@dataclass
class CallSession:
    session_id: str
    channel: str = "Call"  # Call | Text
    language: str = "en"
    customer: dict | None = None
    ticket_id: str | None = None
    history: list[dict] = field(default_factory=list)  # {"role": "user"|"assistant", "content": str}
    state: dict = field(default_factory=dict)  # playbook state (awaiting, order_id, …)
    prior_judgment: Judgment | None = None
    guidance: list[str] = field(default_factory=list)  # human guidance injected into the live AI
    human_active: bool = False  # a person took over; the AI stays quiet
    closed: bool = False
    task: asyncio.Task | None = None
    nudge: asyncio.Task | None = None
    seq: int = 0
    started_at: Any = field(default_factory=utcnow)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    last_agent_text: str = ""

    def cancel_turn(self) -> None:
        if self.task and not self.task.done():
            self.task.cancel()
        if self.nudge and not self.nudge.done():
            self.nudge.cancel()


class SessionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, CallSession] = {}

    def create(self, *, channel: str = "Call", customer: dict | None = None, language: str = "en",
               session_id: str | None = None) -> CallSession:
        sid = session_id or uuid.uuid4().hex[:12]
        s = CallSession(session_id=sid, channel=channel, customer=customer, language=language)
        self._sessions[sid] = s
        return s

    def get(self, session_id: str) -> CallSession | None:
        return self._sessions.get(session_id)

    def by_ticket(self, ticket_id: str) -> CallSession | None:
        for s in self._sessions.values():
            if s.ticket_id == ticket_id:
                return s
        return None

    def active_calls(self) -> int:
        return sum(1 for s in self._sessions.values() if not s.closed)

    def drop(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def clear(self) -> None:
        for s in self._sessions.values():
            s.cancel_turn()
        self._sessions.clear()


sessions = SessionManager()
