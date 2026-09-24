"""Phone calls (docs/architecture.md §2.1, "Call").

A real phone call reaches Resolvyn through any provider that can fork the call audio to a WebSocket. This
module speaks the Twilio Media Streams protocol (8 kHz G.711 mu-law, 20 ms frames, base64 in JSON); Exotel,
Plivo, Knowlarity and others use the same shape with different envelope names.

    caller's phone ──▶ provider ──▶ /ws/telephony/twilio ──▶ mu-law → PCM16 ──▶ Gnani streaming STT (VAD)
                                                                                     │ utterance
    caller's phone ◀── provider ◀── mu-law frames ◀── Gnani TTS (8 kHz mu-law) ◀── conversation pipeline

Barge-in: Gnani's VAD `speech_start` clears the audio still queued at the provider and cancels the agent's turn.
The caller is identified from the number they call from (last four digits) when it matches exactly one customer.
"""

import asyncio
import base64
import json
import time
from xml.sax.saxutils import quoteattr

from fastapi import APIRouter, Request, Response, WebSocket, WebSocketDisconnect
from sqlmodel import Session, select

from app.api.ws import is_echo
from app.config import get_settings
from app.database import engine
from app.models import Customer
from app.services import conversation
from app.services.realtime import hub
from app.services.sessions import sessions
from app.voice import gnani
from app.voice.audio import mulaw_to_pcm16
from app.voice.tts import TTSUnavailable, tts

router = APIRouter()


def _log_task_failure(task: asyncio.Task) -> None:
    if not task.cancelled() and task.exception():
        print(f"[phone] background task crashed: {type(task.exception()).__name__}: {task.exception()}", flush=True)


@router.post("/api/telephony/twilio/voice")
async def twilio_voice(request: Request):
    """Webhook Twilio calls when someone dials your number: connect the call audio to our WebSocket."""
    form = await request.form()
    base = get_settings().public_base_url or f"{request.url.scheme}://{request.headers.get('host', 'localhost:8000')}"
    ws_url = base.replace("https://", "wss://").replace("http://", "ws://").rstrip("/") + "/ws/telephony/twilio"
    caller = str(form.get("From", ""))
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?><Response><Connect>'
        f"<Stream url={quoteattr(ws_url)}><Parameter name=\"from\" value={quoteattr(caller)}/></Stream>"
        "</Connect></Response>"
    )
    return Response(xml, media_type="text/xml")


@router.get("/api/telephony/status")
def telephony_status(request: Request):
    base = get_settings().public_base_url or f"{request.url.scheme}://{request.headers.get('host', 'localhost:8000')}"
    return {
        "ready": gnani.configured(),
        "provider": "twilio-media-streams",
        "webhook_url": base.rstrip("/") + "/api/telephony/twilio/voice",
        "stt": "gnani streaming (8 kHz)" if gnani.configured() else None,
        "tts": "gnani mu-law 8 kHz" if gnani.configured() else None,
    }


def _customer_for(number: str) -> dict | None:
    digits = "".join(c for c in number if c.isdigit())
    if len(digits) < 4:
        return None
    with Session(engine) as s:
        rows = s.exec(select(Customer).where(Customer.phone_last4 == digits[-4:])).all()
    return rows[0].model_dump() if len(rows) == 1 else None


class _Playback:
    """Ordered agent audio for one call, with instant cancel (barge-in)."""

    def __init__(self, ws: WebSocket, stream_sid: str) -> None:
        self.ws, self.sid = ws, stream_sid
        self.queue: asyncio.Queue = asyncio.Queue()
        self.busy_until = 0.0
        self.gen = 0
        self.task = asyncio.create_task(self._run())

    @property
    def speaking(self) -> bool:
        return time.monotonic() < self.busy_until or not self.queue.empty()

    def add(self, text: str, lang: str) -> None:
        print(f"[phone] queue audio: {text[:70]!r}", flush=True)
        # Synthesis starts now (in parallel); playback stays strictly in order.
        fut = asyncio.create_task(tts.synth(text, lang, "mulaw8k"))
        self.queue.put_nowait((self.gen, fut))

    async def clear(self) -> None:
        print("[phone] barge-in: clearing queued agent audio", flush=True)
        self.gen += 1
        while not self.queue.empty():
            _, fut = self.queue.get_nowait()
            fut.cancel()
        self.busy_until = 0.0
        try:
            await self.ws.send_text(json.dumps({"event": "clear", "streamSid": self.sid}))
        except Exception:  # noqa: BLE001
            pass

    async def _run(self) -> None:
        try:
            while True:
                gen, fut = await self.queue.get()
                try:
                    audio = await fut
                except (TTSUnavailable, asyncio.CancelledError, Exception) as e:  # noqa: BLE001
                    print(f"[phone] TTS failed, this sentence is dropped: {type(e).__name__}: {str(e)[:100]}", flush=True)
                    continue
                if gen != self.gen:
                    print("[phone] stale audio dropped (caller interrupted)", flush=True)
                    continue
                now = time.monotonic()
                self.busy_until = max(self.busy_until, now) + len(audio) / 8000.0
                for i in range(0, len(audio), 1600):  # 200 ms per message
                    await self.ws.send_text(json.dumps({
                        "event": "media", "streamSid": self.sid,
                        "media": {"payload": base64.b64encode(audio[i:i + 1600]).decode()},
                    }))
        except (asyncio.CancelledError, WebSocketDisconnect):
            return
        except Exception:  # noqa: BLE001 - socket closed
            return


@router.websocket("/ws/telephony/twilio")
async def twilio_ws(ws: WebSocket):
    await ws.accept()
    session = None
    listener: gnani.Listener | None = None
    playback: _Playback | None = None
    events_task: asyncio.Task | None = None
    q = None
    try:
        while True:
            msg = json.loads(await ws.receive_text())
            event = msg.get("event")

            if event == "start":
                start = msg["start"]
                caller = (start.get("customParameters") or {}).get("from", "")
                customer = _customer_for(caller)
                session = sessions.create(channel="Call", customer=customer)
                playback = _Playback(ws, start["streamSid"])
                q = hub.subscribe_session(session.session_id)

                async def on_transcript(text: str) -> None:
                    if is_echo(session, text):
                        return
                    conversation.submit(session, text)

                async def on_speech_start() -> None:
                    if playback.speaking:  # the caller talks over the agent
                        await playback.clear()
                        conversation.barge_in(session)

                listener = gnani.Listener("en", 8000, on_transcript=on_transcript, on_speech_start=on_speech_start)
                try:
                    await listener.start()
                except gnani.GnaniUnavailable:
                    listener = None  # no STT: the agent can still greet and say goodbye

                async def relay() -> None:
                    nonlocal listener
                    while True:
                        ev = await q.get()
                        if ev.get("type") == "agent_sentence":
                            playback.add(ev.get("say") or ev["text"], ev.get("lang", "en"))
                        elif ev.get("type") == "agent_done" and listener and session.language != ("hi" if listener.language == "hi-IN" else "en"):
                            # the caller switched language: re-open the recogniser in that language
                            lang = session.language
                            await listener.stop()
                            listener = gnani.Listener(lang, 8000, on_transcript=on_transcript, on_speech_start=on_speech_start)
                            try:
                                await listener.start()
                            except gnani.GnaniUnavailable:
                                listener = None

                events_task = asyncio.create_task(relay())
                events_task.add_done_callback(_log_task_failure)
                await conversation.start(session)

            elif event == "media" and listener:
                await listener.feed(mulaw_to_pcm16(base64.b64decode(msg["media"]["payload"])))

            elif event == "stop":
                break
    except WebSocketDisconnect:
        pass
    finally:
        if events_task:
            events_task.cancel()
        if playback:
            playback.task.cancel()
        if listener:
            await listener.stop()
        if q is not None and session:
            hub.unsubscribe_session(session.session_id, q)
        if session:
            await conversation.end_call(session, "phone call ended")
