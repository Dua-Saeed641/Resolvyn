"""System status (models, voice) and the text-to-speech endpoint."""

from pydantic import BaseModel
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


class GuardIn(BaseModel):
    enabled: bool
    prompt_rules: bool | None = None  # the truth rules inside the prompt (benchmark stress condition)


@router.post("/truth-guard")
def truth_guard(body: GuardIn):
    """Switch the truth guard on or off at runtime. Only for the benchmark, which measures the raw model against the guarded one."""
    from app.config import get_settings

    get_settings().truth_guard = body.enabled
    if body.prompt_rules is not None:
        get_settings().truth_prompt = body.prompt_rules
    return {"truth_guard": body.enabled, "truth_prompt": get_settings().truth_prompt}


@router.get("/benchmarks")
def benchmarks():
    """The measured results (backend/benchmarks) merged, later runs replacing the stages they re-measured. Read-only."""
    import json
    from pathlib import Path

    folder = Path(__file__).resolve().parents[3] / "benchmarks"
    merged: dict = {}
    for name in ("results.json", "results_part2.json", "results_part3.json", "results_part4.json", "results_truth.json", "tests.json"):
        f = folder / name
        if f.exists():
            data = json.loads(f.read_text(encoding="utf-8"))
            if name == "tests.json":
                merged["tests"] = data
            elif name == "results_truth.json":
                merged["truth"] = data["truth"]  # only the adversarial section; its timings are not the resolution run's
            else:
                merged.update(data)
    if not merged:
        raise HTTPException(404, "No benchmark results yet. Run: python -m benchmarks.run")
    return merged
