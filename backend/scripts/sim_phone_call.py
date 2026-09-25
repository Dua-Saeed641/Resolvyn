"""Simulate a real phone call against /ws/telephony/twilio (no Twilio account needed).

It plays the part of Twilio's media stream: the caller's lines are synthesised with Gnani TTS as 8 kHz mu-law,
streamed in 20 ms frames at real-time pace, followed by silence so the VAD closes the utterance. Whatever the agent
sends back (mu-law frames) is collected and transcribed with Gnani STT so you can read what she said.

  .venv\\Scripts\\python scripts\\sim_phone_call.py --from "+91 98765 74821" --approve \\
      "Hi, I was charged twice for my order" "The order ID is ORD 83921" "Yes please refund the duplicate one" "Thanks, that's all"

The number's last four digits identify the customer (74821 -> 4821 = Aarav Sharma).
"""

import argparse
import asyncio
import base64
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import httpx  # noqa: E402
import websockets  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from app.voice import gnani  # noqa: E402
from app.voice.audio import mulaw_to_pcm16  # noqa: E402

API = "http://127.0.0.1:8000"
WS = "ws://127.0.0.1:8000/ws/telephony/twilio"
HEADERS = {"ngrok-skip-browser-warning": "1"}
SILENCE = b"\xff" * 160


async def transcribe(mulaw: bytes) -> str:
    """What did the agent say? Feed her audio into Gnani STT."""
    if not mulaw:
        return ""
    pcm = mulaw_to_pcm16(mulaw) + b"\x00" * 16000  # 1 s of silence to close the last segment
    texts: list[str] = []

    async def on_text(t: str) -> None:
        texts.append(t)

    lst = gnani.Listener("en", 8000, on_transcript=on_text)
    await lst.start()
    for i in range(0, len(pcm), 1024):
        await lst.feed(pcm[i:i + 1024].ljust(1024, b"\x00"))
        await asyncio.sleep(1024 / 2 / 8000 / 4)  # 4x real time is accepted for a readback
    await asyncio.sleep(3.0)
    await lst.stop()
    return " ".join(texts)


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("lines", nargs="+")
    ap.add_argument("--from", dest="caller", default="+91 98765 74821")
    ap.add_argument("--approve", action="store_true")
    ap.add_argument("--base", default="", help="public URL of the app (e.g. the ngrok URL): the media stream goes through it, like Twilio")
    ap.add_argument("--voice", default="Pranav", help="voice used for the CALLER audio")
    args = ap.parse_args()

    ws_url = args.base.replace("https://", "wss://").replace("http://", "ws://").rstrip("/") + "/ws/telephony/twilio" if args.base else WS
    async with websockets.connect(ws_url, max_size=None, additional_headers=HEADERS) as ws, httpx.AsyncClient(timeout=30) as http:
        out_frames: list[bytes] = []
        last_media = [0.0]
        first_media_at: list[float] = []

        async def reader():
            async for raw in ws:
                m = json.loads(raw)
                if m.get("event") == "media":
                    if not first_media_at:
                        first_media_at.append(time.perf_counter())
                    out_frames.append(base64.b64decode(m["media"]["payload"]))
                    last_media[0] = time.perf_counter()
                elif m.get("event") == "clear":
                    print("      (agent audio cleared: barge-in)")

        rtask = asyncio.create_task(reader())
        await ws.send(json.dumps({"event": "connected", "protocol": "Call", "version": "1.0.0"}))
        await ws.send(json.dumps({"event": "start", "start": {"streamSid": "MZsim", "callSid": "CAsim", "customParameters": {"from": args.caller}}}))

        async def collect(label: str, quiet: float = 3.5, maxwait: float = 40.0) -> None:
            t0 = time.perf_counter()
            while time.perf_counter() - t0 < maxwait:
                await asyncio.sleep(0.25)
                if out_frames and time.perf_counter() - last_media[0] > quiet:
                    break
            audio = b"".join(out_frames)
            out_frames.clear()
            spoken_s = len(audio) / 8000
            text = await transcribe(audio)
            print(f"      RILEY heard by STT ({spoken_s:.1f}s of audio): {text}" if False else f"      AGENT ({spoken_s:.1f}s of audio): {text}")

        await collect("greeting")
        gate = None
        if args.approve:
            async def approve_loop():
                while True:
                    await asyncio.sleep(1.5)
                    for a in (await http.get(f"{API}/api/human-intelligence/approvals")).json():
                        print(f"      >>> MANAGER approves: {a['summary']}")
                        await http.post(f"{API}/api/human-intelligence/approve", json={"ticket_id": a["ticket_id"], "action_id": a["action_id"], "reason": "verified"})
            gate = asyncio.create_task(approve_loop())

        for line in args.lines:
            print(f"\nCALLER: {line}")
            mu = await gnani.synth(line, "en", "mulaw8k")
            first_media_at.clear()
            for i in range(0, len(mu), 160):
                await ws.send(json.dumps({"event": "media", "streamSid": "MZsim", "media": {"payload": base64.b64encode(mu[i:i + 160].ljust(160, b"\xff")).decode()}}))
                await asyncio.sleep(0.02)
            spoke_until = time.perf_counter()
            for _ in range(75):  # 1.5 s of line noise / silence
                await ws.send(json.dumps({"event": "media", "streamSid": "MZsim", "media": {"payload": base64.b64encode(SILENCE).decode()}}))
                await asyncio.sleep(0.02)
            await collect("reply")
            if first_media_at:
                print(f"      first agent audio {first_media_at[0] - spoke_until:.1f}s after the caller stopped talking")

        await ws.send(json.dumps({"event": "stop"}))
        if gate:
            gate.cancel()
        await asyncio.sleep(2)
        rtask.cancel()
        tickets = (await http.get(f"{API}/api/tickets")).json()
        t = next((x for x in tickets if x["channel"] == "Call" and x["customer_name"]), tickets[0])
        print(f"\nTICKET {t['ticket_id']}: {t['status']} · {t['assigned_agent']} · {t['customer_name']} · {t['resolution_path']}\n  {t['one_line_summary']}")


asyncio.run(main())
