"""Optional free-tier cloud LLM (any OpenAI-compatible endpoint).

Set CLOUD_LLM_BASE_URL / CLOUD_LLM_API_KEY / CLOUD_LLM_MODEL in backend/.env.
Good free options: Groq (llama-3.3-70b-versatile), Google Gemini's OpenAI
compatible endpoint, OpenRouter ':free' models. Latency is far lower than a
4 GB GPU can offer, which makes the live voice loop snappier.
"""

import json
from typing import AsyncIterator

import httpx

from app.config import get_settings
from app.llm.base import LLMUnavailable


class CloudBackend:
    name = "cloud"

    def __init__(self) -> None:
        s = get_settings()
        self.base = (s.cloud_llm_base_url or "").rstrip("/")
        self.key = s.cloud_llm_api_key
        self.model = s.cloud_llm_model
        self.error: str | None = None
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(30, connect=5))

    def configured(self) -> bool:
        return bool(self.base and self.key and self.model)

    def available(self, tier: str) -> bool:  # noqa: ARG002 - one model serves all tiers
        return self.configured()

    async def stream(
        self,
        messages: list[dict],
        *,
        tier: str = "fast",  # noqa: ARG002
        max_tokens: int = 200,
        temperature: float = 0.6,
        json_schema: dict | None = None,
        stop: list[str] | None = None,
    ) -> AsyncIterator[str]:
        if not self.configured():
            raise LLMUnavailable("cloud LLM not configured")
        payload: dict = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }
        if stop:
            payload["stop"] = stop[:4]
        if json_schema is not None:
            payload["response_format"] = {"type": "json_object"}
        auth = get_settings().cloud_llm_auth_header
        headers = {"Authorization": f"Bearer {self.key}"} if auth.lower() == "authorization" else {auth: self.key}
        try:
            async with self._client.stream(
                "POST", f"{self.base}/chat/completions", json=payload, headers=headers
            ) as resp:
                if resp.status_code >= 400:
                    body = (await resp.aread()).decode("utf-8", "replace")[:300]
                    raise LLMUnavailable(f"cloud LLM HTTP {resp.status_code}: {body}")
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    chunk = line[5:].strip()
                    if chunk == "[DONE]":
                        break
                    try:
                        delta = json.loads(chunk)["choices"][0].get("delta", {})
                    except Exception:
                        continue
                    piece = delta.get("content")
                    if piece:
                        yield piece
            self.error = None
        except LLMUnavailable as e:
            self.error = str(e)
            raise
        except httpx.HTTPError as e:
            self.error = str(e)
            raise LLMUnavailable(f"cloud LLM error: {e}") from e

    def status(self) -> dict:
        return {
            "provider": self.name,
            "configured": self.configured(),
            "model": self.model,
            "error": self.error,
        }
