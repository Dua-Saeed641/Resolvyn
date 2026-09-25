"""LLM router: local epsilon engine, optional free cloud model, deterministic fallback.

Order is controlled by LLM_PREFER (local | cloud). If a provider fails *before*
producing output, the next one is tried. If everything fails, LLMUnavailable is
raised and the caller uses its deterministic path.
"""

import asyncio
import json
import re
import time
from typing import AsyncIterator

from app.config import get_settings
from app.llm.base import LLMUnavailable
from app.llm.cloud_backend import CloudBackend
from app.llm.engine_backend import EngineBackend


class LLM:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.engine = EngineBackend()
        self.cloud = CloudBackend()
        self._boot: asyncio.Task | None = None
        self.last_latency_ms: dict[str, int] = {}
        self.last_served: dict[str, str] = {}  # tier -> human-readable model that answered last

    # ── lifecycle ─────────────────────────────────────────────────────────────
    async def start(self) -> None:
        if self.settings.engine_enabled and self._boot is None:
            # Model load takes a while; never block API start-up on it.
            self._boot = asyncio.create_task(self.engine.start())

    async def stop(self) -> None:
        if self._boot:
            self._boot.cancel()
        await self.engine.stop()

    # ── provider order ────────────────────────────────────────────────────────
    def _order(self, tier: str):
        prefer_cloud = self.settings.llm_prefer == "cloud"
        if tier == "deep":
            # Deep = the 27B through epsilon; cloud only if the 27B is not set up.
            return [self.engine, self.cloud]
        return [self.cloud, self.engine] if prefer_cloud else [self.engine, self.cloud]

    @staticmethod
    def _label(backend, tier: str) -> str:
        try:
            st = backend.status()
        except Exception:  # noqa: BLE001
            st = {}
        model = st.get("model") or ((st.get("tiers") or {}).get(tier) or {}).get("model") or backend.name
        model = str(model).replace(".gguf", "").split("/")[-1]
        return f"{model} (local GPU)" if backend.name == "epsilon" else f"{model} (cloud)"

    def ready(self, tier: str = "fast") -> bool:
        return any(b.available(tier) for b in self._order(tier))

    # ── generation ────────────────────────────────────────────────────────────
    async def stream(
        self,
        messages: list[dict],
        *,
        tier: str = "fast",
        max_tokens: int = 200,
        temperature: float = 0.6,
        json_schema: dict | None = None,
        stop: list[str] | None = None,
    ) -> AsyncIterator[str]:
        last_err: Exception | None = None
        for backend in self._order(tier):
            if not backend.available(tier):
                continue
            started = time.perf_counter()
            produced = False
            try:
                async for piece in backend.stream(
                    messages,
                    tier=tier,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    json_schema=json_schema,
                    stop=stop,
                ):
                    if not produced:
                        self.last_served[tier] = self._label(backend, tier)
                        self.last_latency_ms[f"{backend.name}:{tier}:first_token"] = int(
                            (time.perf_counter() - started) * 1000
                        )
                    produced = True
                    yield piece
                return
            except LLMUnavailable as e:
                last_err = e
                if produced:
                    raise
                continue
        raise LLMUnavailable(str(last_err) if last_err else "no LLM available")

    async def complete(self, messages: list[dict], **kwargs) -> str:
        parts = []
        async for piece in self.stream(messages, **kwargs):
            parts.append(piece)
        return "".join(parts).strip()

    async def complete_json(self, messages: list[dict], schema: dict, **kwargs) -> dict:
        """Constrained JSON completion. Raises LLMUnavailable if it cannot parse."""
        text = await self.complete(messages, json_schema=schema, **kwargs)
        try:
            return json.loads(text)
        except Exception:
            m = re.search(r"\{.*\}", text, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group(0))
                except Exception:
                    pass
        raise LLMUnavailable(f"model did not return valid JSON: {text[:120]!r}")

    def status(self) -> dict:
        return {
            "prefer": self.settings.llm_prefer,
            "engine": self.engine.status(),
            "cloud": self.cloud.status(),
            "latency_ms": self.last_latency_ms,
            "live_ready": self.ready("fast"),
            "deep_ready": self.engine.available("deep"),
        }


llm = LLM()
