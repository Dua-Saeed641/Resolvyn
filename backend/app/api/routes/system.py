"""System status (models, voice) and the text-to-speech endpoint."""

from fastapi import APIRouter, HTTPException, Response

from app.config import get_settings
from app.llm import llm
from app.services.realtime import hub
from app.services.sessions import sessions
from app.api.ws import stt_server_available
from app.voice import gnani
from app.voice.tts import tts

router = APIRouter()


@router.get("/system")
def system():
    s = get_settings()
    return {
        "product": s.app_name, "business": s.business_name, "agent": s.agent_name,
        "llm": llm.status(), "tts": tts.status(),
        "stt": {"provider": "gnani" if stt_server_available() else "browser", "gnani": gnani.configured()},
        "live_calls": sessions.active_calls(), "ops_clients": hub.ops_clients,
    }


@router.get("/tts")
async def speak(text: str, lang: str = "en", fmt: str = "mp3"):
    text = text.strip()[:500]
    if not text:
        raise HTTPException(400, "text is empty")
    try:
        audio = await tts.synth(text, "hi" if lang == "hi" else "en")
    except Exception as e:  # noqa: BLE001
        raise HTTPException(503, f"tts unavailable: {e}") from e
    return Response(audio, media_type="audio/mpeg", headers={"Cache-Control": "public, max-age=3600"})
