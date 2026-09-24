"""Smoke test: boot the epsilon engine's fast tier and measure latency/throughput.

Run from backend/:  .venv\\Scripts\\python scripts\\engine_smoke.py [--deep]
"""

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.llm import llm  # noqa: E402

SYSTEM = (
    "You are Riya, a warm customer support agent on a phone call for Nova Retail. "
    "Speak like a real person: short sentences, contractions, an occasional 'umm' or 'hmm'. "
    "Reply in at most two sentences."
)


async def main(deep: bool) -> None:
    t0 = time.perf_counter()
    await llm.engine.start()
    print("engine status:", llm.engine.status())
    print(f"load time: {time.perf_counter() - t0:.1f}s")
    if not llm.ready("fast"):
        print("NOT READY:", llm.engine.error)
        return

    tier = "deep" if deep else "fast"
    msgs = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": "Hi, uh, I was charged twice for my order and I'm kind of annoyed."},
    ]
    for run in range(2):
        t = time.perf_counter()
        first = None
        n = 0
        out = []
        async for piece in llm.stream(msgs, tier=tier, max_tokens=80, temperature=0.6):
            if first is None:
                first = time.perf_counter() - t
            n += 1
            out.append(piece)
        total = time.perf_counter() - t
        print(f"[{tier} run {run}] first token {first*1000:.0f} ms | {n} pieces in {total:.2f}s "
              f"| ~{n/max(total-first,0.001):.1f} tok/s")
        print("  ->", "".join(out).strip())
    await llm.stop()


if __name__ == "__main__":
    asyncio.run(main("--deep" in sys.argv))
