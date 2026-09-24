"""WebSockets — the real-time channels (project.md §45).

/ws/call  the caller's screen: text (or streamed microphone audio) in, agent sentences + ticket out
/ws/ops   the team's screen: every ticket, event, tool call, approval, bug alert

Voice input has two routes. With a Gnani key the browser streams raw microphone audio (PCM16 16 kHz)
over this socket and Gnani's real-time STT (with VAD) turns it into utterances — accurate on Indian
accents and independent of the browser. Without a key the browser's own speech recogniser is used and
sends finished sentences as text.
"""

import asyncio
import json
import re

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlmodel import Session

from app.agents import orchestrator
from app.config import get_settings
from app.database import engine
from app.llm import llm
from app.models import Customer
from app.services import analytics_service, conversation
from app.services import ticket_service as tickets
from app.services.realtime import hub
from app.services.sessions import sessions
from app.voice import gnani

router = APIRouter()

RECONNECT_GRACE = 25.0


async def _pump(ws: WebSocket, q: asyncio.Queue) -> None:
    try:
        while True:
            event = await q.get()
            await ws.send_text(json.dumps(event, default=str))
    except Exception:  # noqa: BLE001 - socket closed; the reader loop handles teardown
        return


def stt_server_available() -> bool:
    return gnani.configured() and get_settings().stt_provider in ("auto", "gnani")


_W = re.compile(r"[a-z0-9ऀ-ॿ]+")


def is_echo(session, text: str) -> bool:
    """True if a transcript is (mostly) the agent's own last words coming back through the speakers."""
    said = " ".join(m["content"] for m in session.history[-3:] if m["role"] == "assistant").lower()
    heard = _W.findall(text.lower())
    if len(heard) < 3 or not said:
        return False
    pool = set(_W.findall(said))
    return sum(w in pool for w in heard) / len(heard) >= 0.75


@router.websocket("/ws/call")
async def call_ws(ws: WebSocket):
    await ws.accept()
    qs = ws.query_params
    channel = "Text" if qs.get("channel") == "Text" else "Call"
    lang = "hi" if qs.get("lang") == "hi" else "en"
    customer = None
    if qs.get("customer_id"):
        with Session(engine) as s:
            c = s.get(Customer, qs["customer_id"])
            customer = c.model_dump() if c else None

    resumed = False
    session = sessions.get(qs["session_id"]) if qs.get("session_id") else None
    if session and not session.closed:
        resumed = True
    else:
        session = sessions.create(channel=channel, customer=customer, language=lang)
    q = hub.subscribe_session(session.session_id)
    pump = asyncio.create_task(_pump(ws, q))
    listener: gnani.Listener | None = None
    try:
        # ── optional server-side speech recognition ──────────────────────────
        stt_mode = "browser"
        if qs.get("stt") == "server" and channel == "Call" and stt_server_available():

            async def on_transcript(text: str) -> None:
                if is_echo(session, text):
                    return
                hub.to_session(session.session_id, {"type": "heard", "text": text})
                conversation.submit(session, text)

            async def on_speech_start() -> None:
                hub.to_session(session.session_id, {"type": "user_speaking"})

            async def on_error(msg: str) -> None:
                hub.to_session(session.session_id, {"type": "stt_error", "message": msg})

            listener = gnani.Listener(lang, 16000, on_transcript=on_transcript, on_speech_start=on_speech_start, on_error=on_error)
            try:
                await listener.start()
                stt_mode = "server"
            except gnani.GnaniUnavailable:
                listener = None

        if resumed:
            await ws.send_text(json.dumps({"type": "ticket", "ticket": tickets.customer_view(session.ticket_id)}))
        else:
            await conversation.start(session)
        await ws.send_text(json.dumps({"type": "session", "session_id": session.session_id, "ticket_id": session.ticket_id,
                                       "llm_ready": llm.ready("fast"), "resumed": resumed, "stt": stt_mode}))
        while True:
            packet = await ws.receive()
            if packet["type"] == "websocket.disconnect":
                break
            if packet.get("bytes") is not None:
                if listener:
                    await listener.feed(packet["bytes"])
                continue
            msg = json.loads(packet["text"])
            kind = msg.get("type")
            if kind == "utterance" and str(msg.get("text", "")).strip():
                conversation.submit(session, str(msg["text"]))
            elif kind == "barge_in":
                conversation.barge_in(session)
            elif kind == "language" and msg.get("lang") in ("en", "hi"):
                session.language = msg["lang"]
            elif kind == "end":
                await conversation.end_call(session, "caller ended the call")
                try:
                    await ws.send_text(json.dumps({"type": "call_ended"}))
                except Exception:  # noqa: BLE001 - the client may already be gone
                    pass
                break
    except WebSocketDisconnect:
        pass
    finally:
        pump.cancel()
        if listener:
            await listener.stop()
        hub.unsubscribe_session(session.session_id, q)
        if not session.closed:
            asyncio.create_task(_end_after_grace(session))


async def _end_after_grace(session) -> None:
    await asyncio.sleep(RECONNECT_GRACE)
    if not hub.session_connected(session.session_id):
        await conversation.end_call(session, "connection lost")


@router.websocket("/ws/ops")
async def ops_ws(ws: WebSocket):
    await ws.accept()
    q = hub.subscribe_ops()
    pump = asyncio.create_task(_pump(ws, q))
    try:
        await ws.send_text(json.dumps({
            "type": "snapshot",
            "tickets": tickets.list_tickets(),
            "agents": orchestrator.list_agents(),
            "stats": analytics_service.stats(),
            "bugs": tickets.open_bugs(),
            "approvals": tickets.pending_for_approval(),
            "events": tickets.recent_events(60),
        }, default=str))
        while True:
            # the ops socket is server → client; reads only detect disconnects and answer pings
            await _tick(ws)
    except WebSocketDisconnect:
        pass
    finally:
        pump.cancel()
        hub.unsubscribe_ops(q)


async def _tick(ws: WebSocket) -> None:
    """Wait for a client message or push fresh stats every few seconds."""
    try:
        await asyncio.wait_for(ws.receive_text(), timeout=4.0)
    except asyncio.TimeoutError:
        await ws.send_text(json.dumps({"type": "stats", "stats": analytics_service.stats(), "agents": orchestrator.list_agents(),
                                       "llm": llm.status()}, default=str))
