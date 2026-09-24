# Epsilon engine (inside Resolvyn)

This folder is a copy of the **epsilon v2** engine (`D:\Personal Projects\epsilon\v2`), plus the changes
Resolvyn needed. Resolvyn's backend uses the engine's `TieredModelManager`
(`engine/backend/tiers/model_manager.py`) to start, feed and stop `llama-server` processes; the rest of
epsilon (IDE agents, Clara, Telegram bot, `AetherLink`) is kept untouched so the original engine still works.

## What Resolvyn runs on it

| Tier | Model | Where | Used for |
|---|---|---|---|
| `fast` | Qwen3.5-4B Q4_K_M (~3 GB) | GPU, fully offloaded (4 GB VRAM) | the live call brain **and** Jev (judgment, ticket notes) |
| `deep` | Qwen3.8-27B IQ2_XXS (~8.9 GB) | CPU + RAM | background analysis after a call (fuller ticket write-up) |

Why the 27B is not the live voice: a dense 27B does not fit in 4 GB of VRAM (smallest usable quant is 8.9 GB), so it
runs on the CPU at about **1.3 tokens/second** here. That is fine for a background write-up and useless for a
spoken conversation, where the 4B answers at ~35 tokens/second with a first token in ~0.3 s. The engine loads the 27B
on demand, never while a caller is on the line, and unloads it (returning ~9 GB of RAM) shortly after.

## Changes made to the copied engine

* `backend/tiers/model_manager.py`
  * `stream()` async generator (tokens as they are produced); `generate()` is now a thin wrapper.
  * runs natively on Windows (no WSL), llama-server output goes to `logs/` instead of `/dev/null`.
  * per-tier `extra_args` and `ports`; `cache_prompt` on; JSON-schema constrained output passthrough.
  * the idle watchdog also unloads the deep tier, and **never kills a tier that is mid-generation**
    (in-flight counter — the original timer was measured from request start and killed long 27B runs).
  * `start_tier()` / `stop_tier()` / `tier_ready()`.
* `bin/` — a current llama.cpp Windows CUDA build (`llama-server.exe`). The BitNet-era build in `BitNet/build`
  predates Qwen3.5 / Qwen3.8 (Gated DeltaNet hybrid attention) and cannot load them.
* `config.resolvyn.yaml` — tier definitions for this machine (RTX A2000 4 GB, 16 GB RAM).

`BitNet/`, `venv/` (Linux virtualenv, not portable) and the original `config.yaml` are epsilon's own. `venv/` was not
copied; recreate it in WSL if you want to run the original IDE engine.

## Setup

```powershell
cd engine
.\download_models.ps1          # llama.cpp CUDA build + Qwen3.5-4B
.\download_models.ps1 -Deep    # + Qwen3.8-27B IQ2_XXS (optional, ~9 GB)
```

Everything under `bin/`, `models/`, `logs/` and `BitNet/` is git-ignored.

## Try it directly

```powershell
cd backend
.venv\Scripts\python scripts\engine_smoke.py           # boots the fast tier, prints latency / tokens per second
.venv\Scripts\python scripts\engine_smoke.py --deep    # same for the 27B (expect ~1 tok/s)
```

Measured on the target laptop: fast tier loads in ~8 s, first token 280–650 ms, ~35–39 tokens/s;
deep tier loads in ~10 s (memory-mapped), ~1.3 tokens/s, ~46 tokens/s prompt processing.
