"""Replay a scripted caller against the running backend and print what the agent says (text channel, real model).

  .venv\\Scripts\\python scripts\\replay_call.py "hi mera naam mukesh hai..." "ismein 3508 likha hai"
  .venv\\Scripts\\python scripts\\replay_call.py --customer CUS-20481 "where is my order"
"""

import argparse
import asyncio
import json
import sys

import websockets

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("lines", nargs="+")
    ap.add_argument("--customer", default="")
    ap.add_argument("--port", type=int, default=8000)
    a = ap.parse_args()
    q = f"channel=Text" + (f"&customer_id={a.customer}" if a.customer else "")
    async with websockets.connect(f"ws://127.0.0.1:{a.port}/ws/call?{q}", max_size=None) as ws:
        async def until_done() -> str:
            said = []
            while True:
                ev = json.loads(await asyncio.wait_for(ws.recv(), 60))
                if ev["type"] == "agent_sentence":
                    said.append(ev["text"])
                if ev["type"] in ("agent_done", "side_talk"):
                    return " ".join(said)

        print("Riya:", await until_done())
        for line in a.lines:
            print("\nYou :", line)
            await ws.send(json.dumps({"type": "utterance", "text": line}))
            print("Riya:", await until_done())


asyncio.run(main())
