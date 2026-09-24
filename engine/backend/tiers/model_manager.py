"""
backend/tiers/model_manager.py
================================
Async 3-tier model manager for the Epsilon engine (used by Resolvyn).

Changes for Resolvyn (on top of Epsilon v2.2):
  - stream() async generator: tokens are yielded as llama-server produces them
    (the live voice loop speaks sentence by sentence, it cannot wait for the
    whole completion). generate() is now a thin wrapper over stream().
  - Works natively on Windows (llama.cpp CUDA build, no WSL) and on Linux.
  - Per-tier `extra_args` and `ports` from config; llama-server output goes to
    engine/logs/ instead of /dev/null so load failures are diagnosable.
  - `cache_prompt` is on: the persona/system prefix is reused between turns.
  - Deep tier (Qwen3.8-27B) has its own process slot and is also unloaded by
    the idle watchdog, so its RAM is returned when nobody needs it.
  - start_tier()/stop_tier()/tier_ready() so callers can pre-warm or free a tier.
  - Graceful fallback: if balanced/deep not found, falls back to fast.
"""

import asyncio
import json
import os
import subprocess
import sys
import time
from enum import Enum
from pathlib import Path
from typing import AsyncIterator

import httpx


class Tier(str, Enum):
    FAST = "fast"
    BALANCED = "balanced"
    DEEP = "deep"


DEFAULT_PORTS = {Tier.FAST: 8088, Tier.BALANCED: 8089, Tier.DEEP: 8090}

TIER_TIMEOUTS = {Tier.FAST: 60, Tier.BALANCED: 120, Tier.DEEP: 900}

# How long to wait for llama-server to become healthy
STARTUP_TIMEOUT = {Tier.FAST: 120, Tier.BALANCED: 150, Tier.DEEP: 600}

DEFAULT_STOP = ["<|im_end|>", "<|endoftext|>"]

_WIN = os.name == "nt"


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


class TieredModelManager:
    def __init__(self, config: dict):
        self.config = config
        self.models_cfg = config.get("models", {})

        # One process slot per tier (fast/balanced share a slot; deep is separate)
        self._proc_main: subprocess.Popen | None = None  # fast or balanced
        self._proc_deep: subprocess.Popen | None = None  # deep only
        self.current_tier: Tier | None = None

        self._last_request: dict[str, float] = {}
        self._inflight: dict[str, int] = {}  # requests currently being served, per tier
        self._idle_timeout: int = config.get("idle_timeout", 300)
        self._deep_idle_timeout: int = config.get("deep_idle_timeout", 120)
        self._start_locks = {t: asyncio.Lock() for t in Tier}
        self._watchdog: asyncio.Task | None = None
        self._log_dir = Path(config.get("log_dir", "logs"))

        self._ports = dict(DEFAULT_PORTS)
        for name, port in (config.get("ports") or {}).items():
            self._ports[Tier(name)] = int(port)

        # Binary path — must be in config
        self._llama_bin = config.get("llama_server_bin", "./BitNet/build/bin/llama-server")

    # ── Public API ────────────────────────────────────────────────────────────

    def port(self, tier: Tier) -> int:
        return self._ports[tier]

    async def startup(self):
        """Start FAST tier on boot + launch idle watchdog."""
        if not await self._tier_available(Tier.FAST):
            _log("[Model] WARNING: fast tier model file not found — startup skipped")
            return
        await self._start_server(Tier.FAST)
        if self._watchdog is None:
            self._watchdog = asyncio.create_task(self._idle_watchdog())

    async def shutdown(self):
        """Kill all running servers and free VRAM."""
        if self._watchdog:
            self._watchdog.cancel()
            self._watchdog = None
        self._kill(self._proc_main)
        self._kill(self._proc_deep)
        self._proc_main = None
        self._proc_deep = None
        self.current_tier = None
        _log("[Model] All servers stopped — VRAM freed")

    def tier_file_exists(self, tier: str) -> bool:
        path = self.models_cfg.get(tier, {}).get("path", "")
        return bool(path) and Path(path).exists()

    def tier_ready(self, tier: str) -> bool:
        t = Tier(tier)
        if t == Tier.DEEP:
            return self._proc_deep is not None and self._proc_deep.poll() is None
        return (
            self._proc_main is not None
            and self._proc_main.poll() is None
            and self.current_tier == t
        )

    async def start_tier(self, tier: str) -> None:
        """Pre-warm a tier (no-op if it is already serving)."""
        t = Tier(tier)
        if not await self._tier_available(t):
            raise RuntimeError(f"{tier} tier model file not found")
        await self._ensure_running(t)

    async def stop_tier(self, tier: str) -> None:
        t = Tier(tier)
        if t == Tier.DEEP:
            self._kill(self._proc_deep)
            self._proc_deep = None
        elif self.current_tier == t:
            self._kill(self._proc_main)
            self._proc_main = None
            self.current_tier = None

    async def stream(
        self,
        prompt: str,
        tier: str = "fast",
        max_tokens: int = 512,
        temperature: float = 0.1,
        repeat_penalty: float = 1.1,
        stop: list | None = None,
        top_p: float | None = None,
        json_schema: dict | None = None,
        grammar: str | None = None,
    ) -> AsyncIterator[str]:
        """Yield generated text pieces as they arrive from llama-server."""
        self._last_request[tier] = time.time()
        t = Tier(tier)

        if not await self._tier_available(t):
            _log(f"[Model] {t.value} tier unavailable — falling back to fast")
            t = Tier.FAST
            if not await self._tier_available(t):
                raise RuntimeError("No model tiers available — check model paths in config")

        await self._ensure_running(t)

        port = self._ports[t]
        payload = {
            "prompt": prompt,
            "n_predict": max_tokens,
            "temperature": temperature,
            "repeat_penalty": repeat_penalty,
            "stop": stop or DEFAULT_STOP,
            "stream": True,
            "cache_prompt": True,
        }
        if top_p is not None:
            payload["top_p"] = top_p
        if json_schema is not None:
            payload["json_schema"] = json_schema
        if grammar is not None:
            payload["grammar"] = grammar

        timeout = httpx.Timeout(TIER_TIMEOUTS[t], connect=10)
        self._inflight[t.value] = self._inflight.get(t.value, 0) + 1
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream(
                    "POST", f"http://127.0.0.1:{port}/completion", json=payload
                ) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        chunk = line[6:]
                        if chunk.strip() == "[DONE]":
                            break
                        try:
                            data = json.loads(chunk)
                        except Exception:
                            continue
                        piece = data.get("content", "")
                        if piece:
                            yield piece
                        if data.get("stop"):
                            break
        except httpx.TimeoutException:
            raise RuntimeError(f"{t.value} tier timed out after {TIER_TIMEOUTS[t]}s")
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"{t.value} tier HTTP error: {e.response.status_code}")
        finally:
            self._inflight[t.value] = max(0, self._inflight.get(t.value, 1) - 1)
            self._last_request[t.value] = time.time()

    async def generate(
        self,
        prompt: str,
        tier: str = "fast",
        max_tokens: int = 512,
        temperature: float = 0.1,
        repeat_penalty: float = 1.1,
        stop: list | None = None,
        **kwargs,
    ) -> str:
        """Non-streaming convenience wrapper (kept for Epsilon's orchestrator)."""
        parts = []
        async for piece in self.stream(
            prompt,
            tier=tier,
            max_tokens=max_tokens,
            temperature=temperature,
            repeat_penalty=repeat_penalty,
            stop=stop,
            **kwargs,
        ):
            parts.append(piece)
        return "".join(parts).strip()

    # ── Server lifecycle ──────────────────────────────────────────────────────

    async def _ensure_running(self, t: Tier) -> None:
        async with self._start_locks[t if t == Tier.DEEP else Tier.FAST]:
            if t == Tier.DEEP:
                if self._proc_deep is None or self._proc_deep.poll() is not None:
                    _log("[Model] Cold start — launching deep tier")
                    await self._start_server(Tier.DEEP)
            else:
                if self._proc_main is None or self._proc_main.poll() is not None:
                    _log(f"[Model] Cold start — launching {t.value}")
                    await self._start_server(t)
                elif t != self.current_tier:
                    await self._swap_to(t)
            if self._watchdog is None:
                self._watchdog = asyncio.create_task(self._idle_watchdog())

    async def _start_server(self, tier: Tier):
        cfg = self.models_cfg.get(tier.value, {})
        path = cfg.get("path", "")
        ngl = cfg.get("gpu_layers", 0)
        ctx = cfg.get("context_len", 2048)
        port = self._ports[tier]

        _log(f"[Model] Starting {tier.value} on port {port} — {Path(path).name}")
        _log(f"[Model] GPU layers: {ngl} | context: {ctx}")

        cmd = [
            self._llama_bin,
            "-m", path,
            "-c", str(ctx),
            "-t", str(cfg.get("cpu_threads", self.config.get("cpu_threads", 4))),
            "--host", "127.0.0.1",
            "--port", str(port),
            "-ngl", str(ngl),
            "--no-webui",
        ]
        cmd += [str(a) for a in cfg.get("extra_args", [])]

        self._log_dir.mkdir(parents=True, exist_ok=True)
        log_file = open(self._log_dir / f"llama-{tier.value}.log", "wb")
        kwargs = {}
        if _WIN:
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
            # llama-server loads its ggml-*.dll next to the exe
            kwargs["cwd"] = str(Path(self._llama_bin).resolve().parent)

        proc = subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT, **kwargs)

        if tier == Tier.DEEP:
            self._proc_deep = proc
        else:
            self._proc_main = proc
            self.current_tier = tier

        try:
            await self._wait_ready(port, proc, timeout=STARTUP_TIMEOUT[tier], tier=tier)
        except Exception:
            self._kill(proc)
            if tier == Tier.DEEP:
                self._proc_deep = None
            else:
                self._proc_main = None
                self.current_tier = None
            raise
        _log(f"[Model] {tier.value} ready on port {port}")

    async def _swap_to(self, tier: Tier):
        """Unload current main tier, load new one."""
        if self.current_tier == tier:
            return
        _log(f"[Model] Swapping {self.current_tier.value if self.current_tier else '?'} → {tier.value}")
        self._kill(self._proc_main)
        self._proc_main = None
        self.current_tier = None
        await asyncio.sleep(0.5)  # let VRAM release
        await self._start_server(tier)

    async def _wait_ready(self, port: int, proc: subprocess.Popen, timeout: int, tier: Tier):
        started = time.time()
        deadline = started + timeout
        n = 0
        async with httpx.AsyncClient(timeout=2) as client:
            while time.time() < deadline:
                if proc.poll() is not None:
                    raise RuntimeError(
                        f"llama-server ({tier.value}) exited with code {proc.returncode} during load.\n"
                        f"See {self._log_dir / f'llama-{tier.value}.log'}\n{self._log_tail(tier)}"
                    )
                try:
                    r = await client.get(f"http://127.0.0.1:{port}/health")
                    if r.status_code == 200 and r.json().get("status") == "ok":
                        return
                except Exception:
                    pass
                await asyncio.sleep(1)
                n += 1
                if n % 10 == 0:
                    _log(f"[Model] {tier.value} still loading... ({int(time.time() - started)}s)")
        raise RuntimeError(
            f"llama-server on port {port} did not become ready in {timeout}s.\n"
            f"Check that the model file exists and {self._llama_bin!r} is executable."
        )

    def _log_tail(self, tier: Tier, lines: int = 12) -> str:
        try:
            text = (self._log_dir / f"llama-{tier.value}.log").read_text(errors="replace")
            return "\n".join(text.splitlines()[-lines:])
        except Exception:
            return ""

    async def _tier_available(self, tier: Tier) -> bool:
        """Return True if the model file for this tier exists on disk."""
        return self.tier_file_exists(tier.value)

    def _kill(self, proc: subprocess.Popen | None):
        if proc is None:
            return
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                proc.kill()

    # ── Idle watchdog ─────────────────────────────────────────────────────────

    async def _idle_watchdog(self, check_interval: int = 15):
        """Unload models after inactivity (fast/balanced slot and the deep slot)."""
        while True:
            await asyncio.sleep(check_interval)
            now = time.time()
            if self._proc_main is not None and self.current_tier is not None:
                last = self._last_request.get(self.current_tier.value)
                busy = self._inflight.get(self.current_tier.value, 0) > 0
                if last and not busy and now - last > self._idle_timeout:
                    name = self.current_tier.value
                    _log(f"[Model] Idle {self._idle_timeout}s — unloading {name}")
                    self._kill(self._proc_main)
                    self._proc_main = None
                    self.current_tier = None
                    self._last_request.pop(name, None)
            if self._proc_deep is not None:
                last = self._last_request.get("deep")
                busy = self._inflight.get("deep", 0) > 0  # never kill a generation that is still running
                if last and not busy and now - last > self._deep_idle_timeout:
                    _log(f"[Model] Idle {self._deep_idle_timeout}s — unloading deep tier (RAM freed)")
                    self._kill(self._proc_deep)
                    self._proc_deep = None

    # ── Diagnostics ───────────────────────────────────────────────────────────

    def status(self) -> dict:
        return {
            "current_tier": self.current_tier.value if self.current_tier else None,
            "main_alive": self._proc_main is not None and self._proc_main.poll() is None,
            "deep_alive": self._proc_deep is not None and self._proc_deep.poll() is None,
            "tiers": {
                name: {
                    "file_present": self.tier_file_exists(name),
                    "model": Path(self.models_cfg.get(name, {}).get("path", "")).name,
                    "description": self.models_cfg.get(name, {}).get("description", ""),
                }
                for name in ("fast", "balanced", "deep")
                if name in self.models_cfg
            },
            "idle_timeout": self._idle_timeout,
        }
