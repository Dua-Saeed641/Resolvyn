"""Application settings, loaded from environment variables / backend/.env.

See docs/architecture.md §3 for what is real vs. simulated. No enterprise
credentials belong here. Everything LLM-related has a deterministic fallback
so the app still runs with no model at all (docs/claude.md, engineering rules).
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(BACKEND_DIR / ".env"), extra="ignore")

    app_name: str = "Resolvyn"
    environment: str = "development"
    database_url: str = f"sqlite:///{(BACKEND_DIR / 'data' / 'resolvyn.db').as_posix()}"
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # ── Business persona (the demo company the agent works for) ──────────────
    business_name: str = "Nova Retail"
    agent_name: str = "Riya"

    # ── Local LLM through the epsilon engine (./engine) ──────────────────────
    engine_dir: str = str(REPO_DIR / "engine")
    engine_config: str = str(REPO_DIR / "engine" / "config.resolvyn.yaml")
    # Start the local models on boot. Turn off to run on cloud/mock only.
    engine_enabled: bool = True

    # ── Optional free cloud LLM (any OpenAI-compatible endpoint) ─────────────
    # Groq (free tier):   https://api.groq.com/openai/v1      llama-3.3-70b-versatile
    # Gemini (free tier): https://generativelanguage.googleapis.com/v1beta/openai  gemini-2.0-flash
    # OpenRouter (free):  https://openrouter.ai/api/v1        meta-llama/llama-3.3-70b-instruct:free
    cloud_llm_base_url: str | None = None
    cloud_llm_api_key: str | None = None
    cloud_llm_model: str | None = None
    # Some providers do not use "Authorization: Bearer" (Sarvam uses api-subscription-key).
    cloud_llm_auth_header: str = "Authorization"
    # local  = epsilon engine first, cloud as fallback
    # cloud  = cloud first (lowest latency on a 4GB GPU), local as fallback
    llm_prefer: str = "local"

    # ── Voice ────────────────────────────────────────────────────────────────
    # Gnani (https://gnani.ai): Indian-accent STT with VAD + neural TTS, both usable on 8 kHz phone audio.
    gnani_api_key: str | None = None
    gnani_tts_model: str = "timbre-v2.5"
    gnani_voice: str = "Nalini"  # female. Audition all voices with scripts/voice_audition.py
    # Text-to-speech order: auto = Gnani when a key is set, then edge-tts, then the browser voice.
    tts_provider: str = "auto"  # auto | gnani | edge
    # Speech-to-text for calls: auto = Gnani streaming when a key is set, else the browser's recogniser.
    stt_provider: str = "auto"  # auto | gnani | browser
    tts_voice_en: str = "en-IN-NeerjaExpressiveNeural"  # edge-tts fallback voices
    tts_voice_hi: str = "hi-IN-SwaraNeural"
    tts_rate: str = "+8%"

    # ── Phone (Twilio Media Streams; any provider that streams 8 kHz mu-law works the same way) ──
    # Map real numbers to demo customers so your own phone is recognised: "+919876543210:CUS-20481,+911234567890:CUS-20517"
    phone_aliases: str = ""
    # Twilio REST credentials: only needed for the "Call me" button (Twilio dials your phone and connects it to the agent)
    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_phone_number: str | None = None  # the Twilio number Twilio calls you from, e.g. +15551234567
    public_base_url: str | None = None  # e.g. https://abc123.ngrok.app — where the phone provider reaches this API

    # ── Decision thresholds ──────────────────────────────────────────────────
    # Refunds above this amount (INR) need a human Approve (docs/project.md §24, §84).
    refund_auto_limit: int = 1000
    # Retrieval score at/above which the rulebook counts as a confident "known path".
    known_path_score: float = 0.5
    # Below this best score in *both* memories, the query is a first-time bug.
    # Between the two thresholds Jev asks the model whether the retrieved text
    # really answers the caller's problem (grounding check).
    first_time_bug_score: float = 0.28

    # Run the 27B "deep" tier for detailed summaries when no call is active.
    deep_summaries: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
