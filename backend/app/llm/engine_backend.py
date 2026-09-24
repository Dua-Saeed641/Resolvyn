"""Local LLM through the epsilon engine (D:\\resolvyn\\engine).

The epsilon TieredModelManager owns the llama-server processes (fast tier =
Qwen3.5-4B on GPU, deep tier = Qwen3.8-27B on CPU). This module only adapts it
to Resolvyn's message-based interface. Nothing else in the app talks to a model
directly (docs/claude.md: modules stay replaceable).
"""

import asyncio
import sys
from pathlib import Path
from typing import AsyncIterator

import yaml

from app.config import get_settings
from app.llm.base import LLMUnavailable, to_chatml


class EngineBackend:
    name = "epsilon"

    def __init__(self) -> None:
        s = get_settings()
        self.engine_dir = Path(s.engine_dir)
        self.cfg_path = Path(s.engine_config)
        self.manager = None
        self.error: str | None = None
        self.loading = False
        self._deep_enabled = s.deep_summaries

    # ── lifecycle ─────────────────────────────────────────────────────────────
    def _load_manager(self):
        if not self.cfg_path.exists():
            raise LLMUnavailable(f"engine config missing: {self.cfg_path}")
        cfg = yaml.safe_load(self.cfg_path.read_text(encoding="utf-8"))
        # Resolve relative paths against the engine folder.
        cfg["llama_server_bin"] = str((self.engine_dir / cfg["llama_server_bin"]).resolve())
        for tier in cfg.get("models", {}).values():
            tier["path"] = str((self.engine_dir / tier["path"]).resolve())
        cfg["log_dir"] = str((self.engine_dir / cfg.get("log_dir", "logs")).resolve())
        if str(self.engine_dir) not in sys.path:
            sys.path.insert(0, str(self.engine_dir))
        from backend.tiers.model_manager import TieredModelManager  # epsilon engine

        return TieredModelManager(cfg)

    async def start(self) -> None:
        """Boot the fast tier. Safe to run as a background task."""
        self.loading = True
        try:
            self.manager = self._load_manager()
            if not Path(self.manager._llama_bin).exists():
                raise LLMUnavailable(f"llama-server not found at {self.manager._llama_bin}")
            await self.manager.startup()
            if not self.manager.tier_ready("fast"):
                raise LLMUnavailable("fast tier did not start (model file missing?)")
            self.error = None
        except Exception as e:  # noqa: BLE001 - surfaced through status()
            self.error = str(e)[:600]
            print(f"[LLM] epsilon engine unavailable: {self.error}", file=sys.stderr, flush=True)
        finally:
            self.loading = False

    async def stop(self) -> None:
        if self.manager:
            await self.manager.shutdown()

    # ── interface ─────────────────────────────────────────────────────────────
    def available(self, tier: str) -> bool:
        if self.manager is None:
            return False
        if tier == "deep":
            return self._deep_enabled and self.manager.tier_file_exists("deep")
        return self.manager.tier_ready("fast") or (
            self.manager.tier_file_exists("fast") and not self.loading and self.error is None
        )

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
        if not self.available(tier):
            raise LLMUnavailable("local engine not ready")
        prompt = to_chatml(messages)
        try:
            async for piece in self.manager.stream(
                prompt,
                tier=tier,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=(stop or []) + ["<|im_end|>", "<|endoftext|>"],
                json_schema=json_schema,
                repeat_penalty=1.05,
                top_p=0.9,
            ):
                yield piece
        except asyncio.CancelledError:
            raise
        except LLMUnavailable:
            raise
        except Exception as e:  # noqa: BLE001
            raise LLMUnavailable(str(e)) from e

    def status(self) -> dict:
        info: dict = {
            "provider": self.name,
            "loading": self.loading,
            "error": self.error,
            "ready": bool(self.manager and self.manager.tier_ready("fast")),
        }
        if self.manager:
            info.update(self.manager.status())
        return info
