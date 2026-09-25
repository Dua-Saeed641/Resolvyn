"""Play a caller over the real /ws/call WebSocket and print what the agent says.

  .venv\\Scripts\\python scripts\\e2e_call.py --customer CUS-20481 --approve \\
      "I was charged twice for my order" "My name is Lovekesh and the order is ORD-83921" "yes please refund it"

--approve       approve any refund the AI sends to the human gate (like a manager would)
--suggest TEXT  answer a first-time-bug alert with this suggestion
"""

import argparse
import sys
import asyncio
import json
import time

import httpx
import websockets

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
API = "http://127.0.0.1:8000"
WS = "ws://127.0.0.1:8000/ws/call"


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("lines", nargs="+")
    ap.add_argument("--customer", default="")
    ap.add_argument("--approve", action="store_true")
    ap.add_argument("--suggest", default="")
    ap.add_argument("--wait", type=float, default=90)
    args = ap.parse_args()

    url = f"{WS}?channel=Text" + (f"&customer_id={args.customer}" if args.customer else "")
    t0 = time.perf_counter()
    async with websockets.connect(url) as ws, httpx.AsyncClient(timeout=30) as http:
        ticket_id = None
        done = asyncio.Event()
        first_sentence_at: list[float] = []
        turn_started = [0.0]

        async def reader():
            nonlocal ticket_id
            async for raw in ws:
                ev = json.loads(raw)
                t = ev["type"]
                now = time.perf_counter() - t0
                if t == "session":
                    ticket_id = ev["ticket_id"]
                    print(f"[{now:5.1f}s] SESSION ticket={ticket_id} llm_ready={ev['llm_ready']}")
                elif t == "agent_sentence":
                    if turn_started[0] and not first_sentence_at:
                        first_sentence_at.append(time.perf_counter() - turn_started[0])
                    print(f"[{now:5.1f}s] {'(filler) ' if ev['filler'] else ''}AGENT: {ev['text']}")
                elif t == "agent_done":
                    done.set()
                elif t == "side_talk":
                    print(f"[{now:5.1f}s] SIDE-TALK detected (agent silent): {ev['text']!r} — {ev['reason']}")
                    done.set()
                elif t == "ticket":
                    tk = ev["ticket"]
                    print(f"[{now:5.1f}s]   ticket {tk['ticket_id']} {tk['status']} dept={tk['department']} timeline={len(tk['timeline'])}")
                elif t == "call_ended":
                    return

        rtask = asyncio.create_task(reader())

        async def human_gate():
            while True:
                await asyncio.sleep(1.5)
                if not ticket_id:
                    continue
                if args.approve:
                    for a in (await http.get(f"{API}/api/human-intelligence/approvals")).json():
                        if a["ticket_id"] == ticket_id:
                            print(f"      >>> MANAGER approves: {a['summary']}")
                            await http.post(f"{API}/api/human-intelligence/approve",
                                            json={"ticket_id": ticket_id, "action_id": a["action_id"], "reason": "Duplicate verified"})
                if args.suggest:
                    for b in (await http.get(f"{API}/api/human-intelligence/bugs")).json():
                        if b["ticket_id"] == ticket_id and b["status"] == "OPEN":
                            print(f"      >>> MANAGER suggests for bug {b['bug_id']}: {args.suggest}")
                            await http.post(f"{API}/api/human-intelligence/bugs/{b['bug_id']}/suggest", json={"suggestion": args.suggest})

        gate = asyncio.create_task(human_gate())
        await asyncio.wait_for(done.wait(), 20)  # greeting
        for line in args.lines:
            done.clear()
            first_sentence_at.clear()
            print(f"\n[{time.perf_counter() - t0:5.1f}s] CALLER: {line}")
            turn_started[0] = time.perf_counter()
            await ws.send(json.dumps({"type": "utterance", "text": line}))
            try:
                await asyncio.wait_for(done.wait(), args.wait)
            except asyncio.TimeoutError:
                print("      (timeout waiting for the agent)")
            if first_sentence_at:
                print(f"      first spoken words after {first_sentence_at[0]*1000:.0f} ms")
            # if the AI is waiting on a human, give the gate time to act and speak
            await asyncio.sleep(0.5)
            tk = (await http.get(f"{API}/api/tickets/{ticket_id}")).json()
            if tk["status"] == "WAITING_FOR_HUMAN" and (args.approve or args.suggest):
                done.clear()
                try:
                    await asyncio.wait_for(done.wait(), 40)
                except asyncio.TimeoutError:
                    print("      (no proactive reply after the human acted)")
        await ws.send(json.dumps({"type": "end"}))
        await asyncio.sleep(2)
        gate.cancel()
        rtask.cancel()
        tk = (await http.get(f"{API}/api/tickets/{ticket_id}")).json()
        print("\n=== FINAL TICKET ===")
        for k in ("ticket_id", "status", "assigned_agent", "intent", "sentiment", "priority", "confidence", "resolution_path",
                  "handled_by", "escalated", "is_first_time_bug", "customer_name", "subject", "one_line_summary", "next_step", "jira_key", "jira_status"):
            print(f"  {k}: {tk.get(k)}")
        print("  detailed_summary:", tk.get("detailed_summary"))
        print("  events:")
        for e in tk["events"]:
            print(f"    {e['timestamp'][11:19]} [{e['agent']}] {e['event_type']}: {e['description']}")
        print("  tool calls:", [(c["tool_name"], c["status"]) for c in tk["tool_calls"]])


asyncio.run(main())
