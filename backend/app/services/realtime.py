"""In-process pub/sub used by the WebSocket endpoints.

Two audiences (docs/architecture.md §2.4): the *ops* side (manager / team
dashboard, everything) and the *session* side (the caller's own screen,
customer-safe data only).
"""

import asyncio
from collections import defaultdict


class Hub:
    def __init__(self) -> None:
        self._ops: set[asyncio.Queue] = set()
        self._sessions: dict[str, set[asyncio.Queue]] = defaultdict(set)

    @staticmethod
    def _put(q: asyncio.Queue, event: dict) -> None:
        if q.full():  # slow consumer: drop the oldest instead of blocking the pipeline
            try:
                q.get_nowait()
            except asyncio.QueueEmpty:
                pass
        q.put_nowait(event)

    # ops side
    def subscribe_ops(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=2000)
        self._ops.add(q)
        return q

    def unsubscribe_ops(self, q: asyncio.Queue) -> None:
        self._ops.discard(q)

    def to_ops(self, event: dict) -> None:
        for q in list(self._ops):
            self._put(q, event)

    # caller side
    def subscribe_session(self, session_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=2000)
        self._sessions[session_id].add(q)
        return q

    def unsubscribe_session(self, session_id: str, q: asyncio.Queue) -> None:
        self._sessions[session_id].discard(q)
        if not self._sessions[session_id]:
            self._sessions.pop(session_id, None)

    def to_session(self, session_id: str | None, event: dict) -> None:
        if not session_id:
            return
        for q in list(self._sessions.get(session_id, ())):
            self._put(q, event)

    def session_connected(self, session_id: str | None) -> bool:
        return bool(session_id and self._sessions.get(session_id))

    @property
    def ops_clients(self) -> int:
        return len(self._ops)


hub = Hub()
