"""Realtime broadcast layer — docs/architecture.md §3 (WebSocket preferred,
short polling fallback). No Kafka/Redis: an in-memory connection manager is
enough for a single-process prototype (spec §40: don't add infra that
doesn't materially improve the current build).

Every state-changing service call (ticket_engine, human_service,
learning_service) calls `manager.broadcast(...)` after committing, so
every connected dashboard tab stays in sync without a page refresh.

FastAPI runs a plain `def` route handler in a worker thread, so service
code triggered by those routes calls broadcast() from a thread with no
running event loop. `asyncio.run_coroutine_threadsafe` against the loop
captured at startup is the correct, thread-safe way to hand work back to
it — plain `create_task`/`get_event_loop()` would raise (or, on older
Pythons, silently spin up an unrelated loop).
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self.loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self.loop = loop

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)

    def broadcast(self, event_type: str, payload: dict[str, Any]) -> None:
        """Thread-safe fire-and-forget broadcast, callable from sync or
        async service code, on the event loop thread or a worker thread."""
        if self.loop is None or not self._connections:
            return
        message = json.dumps(
            {"type": event_type, "payload": payload, "timestamp": datetime.now(timezone.utc).isoformat()},
            default=str,
        )
        for connection in list(self._connections):
            asyncio.run_coroutine_threadsafe(self._send_safe(connection, message), self.loop)

    async def _send_safe(self, connection: WebSocket, message: str) -> None:
        try:
            await connection.send_text(message)
        except Exception:
            self.disconnect(connection)

    def schedule(self, coro) -> None:
        """Schedule a coroutine (e.g. the demo run) from any thread."""
        if self.loop is None:
            raise RuntimeError("Event loop not bound yet — app hasn't started.")
        asyncio.run_coroutine_threadsafe(coro, self.loop)


manager = ConnectionManager()
