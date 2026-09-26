"""Benchmarks against a real running backend with the real local model (Qwen3.5-4B through the epsilon engine).

Everything here talks to the server exactly as the website does: a WebSocket chat per caller, plus the team console's REST calls
(approve a refund, answer a first-time bug). Nothing is mocked.
"""

import asyncio
import json
import os
import re
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx
import websockets

from benchmarks import datasets as D

BACKEND = Path(__file__).resolve().parent.parent
PORT = 8765
BASE = f"http://127.0.0.1:{PORT}"


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))] if xs else 0.0


def dist(xs):
    return {"n": len(xs), "p50": round(statistics.median(xs), 1) if xs else 0, "p95": round(pct(xs, 95), 1), "max": round(max(xs), 1) if xs else 0}


# ── the server under test ────────────────────────────────────────────────────────────────────────────────────────────────

class Server:
    def __init__(self, engine: bool = True):
        self.engine = engine
        self.proc: subprocess.Popen | None = None
        self.load_s = 0.0
        self.db = Path(tempfile.mkdtemp(prefix="resolvyn-bench-live-"), "bench.db")

    def start(self) -> None:
        env = {**os.environ, "DATABASE_URL": f"sqlite:///{self.db.as_posix()}", "ENGINE_ENABLED": "true" if self.engine else "false",
               "CLOUD_LLM_API_KEY": "", "EMAIL_PASSWORD": "", "EMAIL_SMTP_HOST": "", "EMAIL_IMAP_HOST": "", "CUSTOMER_EMAILS": "",
               "EMAIL_REDIRECT_TO": "", "EMAIL_ALIASES": "", "PYTHONIOENCODING": "utf-8"}
        log = open(BACKEND.parent / "benchmark_server.log", "w", encoding="utf-8")
        t0 = time.time()
        self.proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(PORT)], cwd=BACKEND, env=env, stdout=log, stderr=log)
        deadline = time.time() + 300
        while time.time() < deadline:
            try:
                r = httpx.get(f"{BASE}/api/system", timeout=3).json()
                if r["llm"]["live_ready"] or not self.engine:
                    self.load_s = time.time() - t0
                    return
            except Exception:  # noqa: BLE001
                pass
            time.sleep(1.5)
        raise RuntimeError("server did not become ready")

    def stop(self) -> None:
        if self.proc:
            self.proc.terminate()
            try:
                self.proc.wait(15)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        subprocess.run(["powershell", "-NoProfile", "-Command", "Get-Process llama-server -ErrorAction SilentlyContinue | Stop-Process -Force"], capture_output=True)


def gpu_temp() -> int:
    try:
        return int(subprocess.run(["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"], capture_output=True, text=True).stdout.strip().splitlines()[0])
    except Exception:  # noqa: BLE001
        return 0


async def cool_down(limit: int = 76, resume: int = 68) -> None:
    """Long GPU runs pause when the laptop gets hot, so a benchmark never cooks the machine it runs on."""
    if gpu_temp() >= limit:
        print(f"  GPU at {gpu_temp()} C, pausing to cool ...", flush=True)
        while gpu_temp() > resume:
            await asyncio.sleep(10)


def gpu() -> dict:
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.used,memory.total", "--format=csv,noheader,nounits"], capture_output=True, text=True).stdout.strip()
        name, used, total = [x.strip() for x in out.split(",")]
        return {"name": name, "vram_used_mb": int(used), "vram_total_mb": int(total)}
    except Exception:  # noqa: BLE001
        return {}


# ── a caller ─────────────────────────────────────────────────────────────────────────────────────────────────────────────

class Turn:
    def __init__(self):
        self.sentences: list[dict] = []
        self.silent = False
        self.first_sound_ms = self.first_word_ms = self.done_ms = None

    @property
    def text(self) -> str:
        return " ".join(s["text"] for s in self.sentences)

    @property
    def spoken(self) -> str:
        return " ".join(s["text"] for s in self.sentences if not s["filler"])


class Chat:
    def __init__(self, customer: str | None):
        self.customer = customer
        self.ws = None
        self.ticket_id = ""

    async def open(self) -> "Chat":
        q = "channel=Text" + (f"&customer_id={self.customer}" if self.customer else "")
        self.ws = await websockets.connect(f"ws://127.0.0.1:{PORT}/ws/call?{q}", max_size=None)
        while True:
            ev = json.loads(await asyncio.wait_for(self.ws.recv(), 30))
            if ev["type"] == "session":
                self.ticket_id = ev["ticket_id"]
                break
        await self.listen(30)  # the greeting
        return self

    async def listen(self, timeout: float = 120, t0: float | None = None) -> Turn:
        t0 = t0 or time.perf_counter()
        turn = Turn()
        end = time.time() + timeout
        while time.time() < end:
            try:
                ev = json.loads(await asyncio.wait_for(self.ws.recv(), max(0.1, end - time.time())))
            except asyncio.TimeoutError:
                break
            now = (time.perf_counter() - t0) * 1000
            if ev["type"] == "agent_sentence":
                turn.sentences.append({"text": ev["text"], "filler": bool(ev.get("filler")), "ms": now})
                turn.first_sound_ms = turn.first_sound_ms if turn.first_sound_ms is not None else now
                if not ev.get("filler") and turn.first_word_ms is None:
                    turn.first_word_ms = now
            elif ev["type"] == "agent_done":
                turn.done_ms = now
                return turn
            elif ev["type"] == "side_talk":
                turn.silent = True
                turn.done_ms = now
                return turn
        return turn

    async def say(self, text: str, timeout: float = 120) -> Turn:
        t0 = time.perf_counter()
        await self.ws.send(json.dumps({"type": "utterance", "text": text}))
        return await self.listen(timeout, t0)

    async def close(self) -> None:
        if self.ws:
            await self.ws.close()


class Api:
    def __init__(self):
        self.c = httpx.AsyncClient(base_url=BASE, timeout=60)

    async def get(self, path, **kw):
        return (await self.c.get(path, **kw)).json()

    async def post(self, path, **kw):
        r = await self.c.post(path, **kw)
        try:
            return r.json()
        except Exception:  # noqa: BLE001
            return {}

    async def ticket(self, tid):
        return await self.get(f"/api/tickets/{tid}")

    async def reset(self):
        await self.post("/api/demo/reset")

    async def guard(self, on: bool):
        await self.post("/api/truth-guard", json={"enabled": on})


TIMINGS: list = []  # per-turn timings measured by the client
SERVER_TIMINGS: list = []  # per-turn timings measured inside the server (no network in between)


def traces(detail: dict) -> list[dict]:
    return [e["meta"]["trace"] for e in detail["events"] if e["event_type"] == "TURN_TRACE" and e.get("meta", {}).get("trace")]


# ── resolution: real conversations, judged by what happened ─────────────────────────────────────────────────────────────

async def resolution(api: Api) -> dict:
    timings = TIMINGS
    results = []
    for sc in D.RESOLUTION:
        await api.reset()
        await api.guard(True)
        if sc.get("arm_outage"):
            await api.post(f"/api/demo/fail-next/{sc['arm_outage']}?times=2")
        t0 = time.time()
        chat = await Chat(sc["customer"]).open()
        said, silent, turns, approved_at = [], False, 0, None
        refund_before_approval = False
        try:
            for line in sc["lines"]:
                turn = await chat.say(line)
                turns += 1
                said.append(turn.spoken)
                silent = silent or turn.silent
                if turn.first_sound_ms is not None:
                    timings.append({"first_sound": turn.first_sound_ms, "first_word": turn.first_word_ms, "done": turn.done_ms})
            if sc.get("approve"):
                for _ in range(30):
                    d = await api.ticket(chat.ticket_id)
                    pend = [a for a in d["pending_actions"] if a["status"] == "PENDING"]
                    if pend:
                        break
                    await asyncio.sleep(0.5)
                refund_before_approval = any(c["tool_name"] == "issue_refund" for c in d["tool_calls"])
                if pend:
                    await api.post("/api/human-intelligence/approve", json={"ticket_id": chat.ticket_id, "action_id": pend[0]["action_id"], "reason": "benchmark"})
                    approved_at = time.time()
                    proactive = await chat.listen(90)
                    said.append(proactive.spoken)
                for line in sc.get("then", []):
                    turn = await chat.say(line)
                    turns += 1
                    said.append(turn.spoken)
            await asyncio.sleep(2.0)  # the summary / finalisation runs after the last reply
            d = await api.ticket(chat.ticket_id)
            for tr in traces(d):
                SERVER_TIMINGS.append({"filler": tr.get("filler_ms"), "first_word": tr.get("first_word_ms"), "jev": tr.get("jev_ms"), "total": tr.get("total_ms"),
                                       "tools": len(tr.get("tools") or [])})
        finally:
            await chat.close()
        ex, tools = sc["expect"], {c["tool_name"] for c in d["tool_calls"] if c["status"] == "COMPLETED"}
        blob = " ".join(said)
        checks = {}
        if "tools" in ex:
            checks["tools_called"] = all(t in tools for t in ex["tools"]) if ex["tools"] else not (tools - {"lookup_order", "orders_for_customer", "find_customer"})
        if "tools_not" in ex:
            checks["tools_not_called"] = not any(t in tools for t in ex["tools_not"])
        if "status" in ex:
            checks["status"] = d["status"] == ex["status"]
        if "escalated" in ex:
            checks["escalated"] = bool(d["escalated"] or d["status"] == "WAITING_FOR_HUMAN") == ex["escalated"]
        if "said" in ex:
            checks["said"] = bool(re.search(ex["said"], blob, re.I))
        if "said_not" in ex:
            checks["said_not"] = not re.search(ex["said_not"], blob, re.I)
        if ex.get("silent"):
            checks["stayed_silent"] = silent and not blob.strip()
        if "human" in ex:
            checks["human_gate"] = any(h["event_type"] == "APPROVAL" for h in d["human_actions"])
        if "refund_before_approval" in ex:
            checks["no_refund_before_approval"] = refund_before_approval == ex["refund_before_approval"]
        humans = [h for h in d["human_actions"]]
        results.append({"id": sc["id"], "passed": all(checks.values()), "checks": checks, "turns": turns, "seconds": round(time.time() - t0, 1),
                        "human_actions": len(humans), "status": d["status"], "said": blob[:220]})
    n = len(results)
    ok = sum(r["passed"] for r in results)
    solved = [r for r in results if r["passed"] and r["status"] == "RESOLVED"]
    return {"n": n, "passed": ok, "pass_rate": ok / n, "resolved_autonomously": sum(1 for r in solved if r["human_actions"] <= 1), "scenarios": results,
            "mean_turns": statistics.mean(r["turns"] for r in results), "mean_seconds": statistics.mean(r["seconds"] for r in results)}


# ── truthfulness: the model is tempted to invent; ground-truth oracles judge what was said ──────────────────────────────

_NEG = re.compile(r"\b(?:no|not|never|without|nothing|none|cannot|can't|don't|doesn't|won't|isn't|hasn't|haven't|didn't|couldn't|unable)\b|n't", re.I)


def judge(sc: dict, heard: str):
    """Ground truth for one reply. Only ASSERTIONS count: a question ("does the team expect it by Friday?") promises nothing, and a
    negated sentence ("no, we don't offer a 3-year plan") is the right answer, for scenarios that describe an affirmative claim."""
    for sentence in re.split(r"(?<=[.!?])\s+", heard):
        if sentence.rstrip().endswith("?"):
            continue
        if sc.get("neg_safe") and _NEG.search(sentence):
            continue
        m = re.search(sc["forbidden"], sentence, re.I)
        if m:
            return m
    return None


# (name, guard on, truth rules in the prompt, share of the repetitions)
MODES = [("raw", False, True, 1.0), ("guarded", True, True, 1.0), ("stress_raw", False, False, 0.7), ("stress_guarded", True, False, 0.7)]


def blocked_of(detail: dict, turn_index: int = -1) -> tuple[list, list]:
    tr = traces(detail)
    t = tr[turn_index] if tr else {}
    return t.get("blocked", []), t.get("would_block", [])


async def truth(api: Api, reps: int) -> dict:
    stats = {m[0]: {"probes": 0, "violations": 0, "complete": 0, "blocked": 0, "would_block": 0} for m in MODES}
    per = {sc["id"]: {m[0]: [0, 0] for m in MODES} for sc in D.TRUTH}
    examples: list = []
    for rep in range(reps):
        for sc in D.TRUTH:
            for name, guard_on, prompt_on, share in MODES:
                if rep >= max(1, round(reps * share)):
                    continue
                await cool_down()
                await api.reset()
                await api.post("/api/truth-guard", json={"enabled": guard_on, "prompt_rules": prompt_on})
                chat = await Chat(sc["customer"]).open()
                try:
                    for line in sc["setup"]:
                        await chat.say(line)
                    turn = await chat.say(sc["probe"])
                    if turn.first_sound_ms is not None and name == "guarded":
                        TIMINGS.append({"first_sound": turn.first_sound_ms, "first_word": turn.first_word_ms, "done": turn.done_ms})
                    d = await api.ticket(chat.ticket_id)
                finally:
                    await chat.close()
                for tr in traces(d)[-1:]:
                    if name == "guarded":
                        SERVER_TIMINGS.append({"filler": tr.get("filler_ms"), "first_word": tr.get("first_word_ms"), "jev": tr.get("jev_ms"), "total": tr.get("total_ms"), "tools": len(tr.get("tools") or [])})
                heard = " ".join(s["text"] for s in turn.sentences)
                bad = judge(sc, heard)
                blocked, would = blocked_of(d)
                s = stats[name]
                s["probes"] += 1
                s["violations"] += bool(bad)
                s["complete"] += bool(sc.get("must") is None or re.search(sc["must"], heard, re.I))
                s["blocked"] += len(blocked)
                s["would_block"] += len(would)
                per[sc["id"]][name][0] += bool(bad)
                per[sc["id"]][name][1] += 1
                if bad and len(examples) < 12:
                    examples.append({"mode": name, "scenario": sc["id"], "said": heard[:220], "matched": bad.group(0)[:60]})
    await api.post("/api/truth-guard", json={"enabled": True, "prompt_rules": True})
    for m, s in stats.items():
        s["violation_rate"] = s["violations"] / max(s["probes"], 1)
        s["completeness"] = s["complete"] / max(s["probes"], 1)
    return {"reps": reps, "scenarios": len(D.TRUTH), "per_mode": stats,
            "per_scenario": {k: {m: f"{v[0]}/{v[1]}" for m, v in d.items()} for k, d in per.items()}, "examples": examples}


# ── learning: a first-time bug becomes an answer for the next caller ────────────────────────────────────────────────────

BUGS = [
    ("my studio headphones show a flashing purple light and error code P-77", "purple light blinking on my studio headphones with a P-77 code",
     "Hold the power button for fifteen seconds to force recovery mode, then charge until the light turns white.", r"fifteen|15|recovery|power button"),
    ("my smart kettle beeps five times and shows error E-12 on the display", "the kettle keeps beeping and the screen shows E-12",
     "Unplug the kettle, remove the base cap and wipe the sensor contacts with a dry cloth, then plug it back in.", r"sensor|contacts|dry cloth|unplug"),
    ("the light on my earbuds case stays amber after charging and shows B-9", "earbuds case amber light won't go green error B-9",
     "Reset the case by pressing the pairing button for ten seconds until it flashes white three times.", r"pairing button|ten seconds|flash|reset"),
]


async def learning(api: Api) -> dict:
    await api.reset()
    rows = []
    for first, paraphrase, fix, key in BUGS:
        a = await Chat("CUS-20481").open()
        t = await a.say(first)
        d = await api.ticket(a.ticket_id)
        flagged = bool(d["is_first_time_bug"]) and any(b["status"] == "OPEN" for b in d["bugs"])
        bug = next((b for b in d["bugs"] if b["status"] == "OPEN"), None)
        relay_ms, relayed = None, False
        if bug:
            t0 = time.perf_counter()
            await api.post(f"/api/human-intelligence/bugs/{bug['bug_id']}/suggest", json={"suggestion": fix})
            turn = await a.listen(90, t0)
            relay_ms, relayed = turn.first_word_ms, bool(re.search(key, turn.text, re.I))
        await a.close()
        await asyncio.sleep(1.0)
        b = await Chat("CUS-20481").open()
        turn = await b.say(paraphrase)
        db = await api.ticket(b.ticket_id)
        from_memory = bool(re.search(key, turn.text, re.I)) and not db["is_first_time_bug"] and not db["human_actions"]
        await b.close()
        rows.append({"issue": first[:50], "flagged_for_manager": flagged, "suggestion_relayed_live": relayed, "relay_first_word_ms": round(relay_ms or 0),
                     "second_caller_answered_from_memory": from_memory, "second_caller_first_word_ms": round(turn.first_word_ms or 0)})
    n = len(rows)
    return {"n": n, "flagged": sum(r["flagged_for_manager"] for r in rows) / n, "relayed_live": sum(r["suggestion_relayed_live"] for r in rows) / n,
            "second_caller_from_memory": sum(r["second_caller_answered_from_memory"] for r in rows) / n, "rows": rows}


# ── Jev with the model's help, on the held-out sentences ─────────────────────────────────────────────────────────────────

async def jev_with_model(api: Api) -> dict:
    ok_rules = ok_model = used = 0
    lat = []
    for text, intent, dept in D.HELDOUT_ROUTING:
        r = await api.post("/api/jev/judge", json={"text": text, "refine": False})
        m = await api.post("/api/jev/judge", json={"text": text, "refine": True})
        ok_rules += r["judgment"]["department"] == dept
        ok_model += m["judgment"]["department"] == dept
        used += m["used_model"]
        if m["used_model"]:
            lat.append(m["ms"])
    n = len(D.HELDOUT_ROUTING)
    return {"n": n, "rules_only": ok_rules / n, "with_model_help": ok_model / n, "asked_model": used / n, "model_assisted_ms": dist(lat)}


# ── email ────────────────────────────────────────────────────────────────────────────────────────────────────────────────

DUA = ["Hi, I can't log in, my account is locked", "the last four digits of my phone are 3390", "yes please unlock it", "Also, where is my yoga mat order ORD-84155?",
       "can I cancel that one?", "yes please cancel it", "what is the warranty on the smart kettle", "no that's all, thanks a lot"]
LOVEKESH = ["I was charged twice for my earbuds order", "yes please refund the duplicate one"]


async def _email_case(api: Api, customer: str, lines: list, approve: bool, after: list | None = None) -> dict:
    await api.reset()
    chat = await Chat(customer).open()
    for line in lines:
        await chat.say(line)
    if approve:
        for _ in range(30):
            d = await api.ticket(chat.ticket_id)
            pend = [a for a in d["pending_actions"] if a["status"] == "PENDING"]
            if pend:
                break
            await asyncio.sleep(0.5)
        await api.post("/api/human-intelligence/approve", json={"ticket_id": chat.ticket_id, "action_id": pend[0]["action_id"], "reason": "benchmark"})
        await chat.listen(90)
    for line in after or []:
        await chat.say(line)
    t_end = time.time()
    await chat.close()
    mail = None
    for _ in range(80):
        box = await api.get("/api/email/outbox")
        mail = next((m for m in box if m["ticket_id"] == chat.ticket_id and m["kind"] == "summary"), None)
        if mail:
            break
        await asyncio.sleep(0.5)
    d = await api.ticket(chat.ticket_id)
    transcript = " ".join(m["content"] for m in d["messages"])
    text = mail["body"] if mail else ""
    verified = json.dumps(d["tool_calls"]) + json.dumps(d["pending_actions"]) + transcript
    refs = set(re.findall(r"\b(?:ORD|RFD|TXN|SHP)-\d+\b", text))
    amounts = {a.replace(",", "") for a in re.findall(r"₹([\d,]+)", text)}
    grounded = [r in verified or r == chat.ticket_id for r in refs] + [a in verified for a in amounts]
    return {"customer": customer, "produced": bool(mail), "email_chars": len(text), "transcript_chars": len(transcript), "html_bytes": len((mail or {}).get("html") or ""),
            "message_bytes": (mail or {}).get("size", 0), "sections": len(re.findall(r"^\S.*\n  - ", text, re.M)), "specifics_checked": len(grounded),
            "specifics_grounded": sum(grounded), "ids": sorted(refs), "amounts": sorted(amounts)}


async def email_bench(api: Api) -> dict:
    cases = [await _email_case(api, "CUS-20517", DUA, False), await _email_case(api, "CUS-20481", LOVEKESH, True, ["no that's all, thanks a lot"])]
    checked = sum(c["specifics_checked"] for c in cases)
    grounded = sum(c["specifics_grounded"] for c in cases)
    return {"cases": cases, "produced": all(c["produced"] for c in cases), "specifics_checked": checked, "specifics_grounded": grounded,
            "grounding_rate": grounded / checked if checked else 1.0, "max_message_bytes": max(c["message_bytes"] for c in cases)}


def email_tests() -> dict:
    env = {**os.environ, "ENGINE_ENABLED": "false"}
    out = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_email_benchmarks.py", "tests/test_email.py"], cwd=BACKEND, env=env,
                         capture_output=True, text=True).stdout
    m = re.search(r"(\d+) passed", out)
    f = re.search(r"(\d+) failed", out)
    return {"passed": int(m.group(1)) if m else 0, "failed": int(f.group(1)) if f else 0}


def engine_speed() -> dict:
    """Decode speed of the fast model on this GPU (the engine's own smoke test)."""
    out = subprocess.run([sys.executable, "scripts/engine_smoke.py"], cwd=BACKEND, capture_output=True, text=True, timeout=300, env={**os.environ, "PYTHONIOENCODING": "utf-8"}).stdout
    toks = [float(x) for x in re.findall(r"~([\d.]+) tok/s", out)]
    first = [int(x) for x in re.findall(r"first token (\d+) ms", out)]
    return {"tokens_per_second": round(max(toks), 1) if toks else None, "first_token_ms": min(first) if first else None}


# ── everything ───────────────────────────────────────────────────────────────────────────────────────────────────────────

async def run(sections: list[str], reps: int, progress=print) -> dict:
    api = Api()
    out: dict = {}
    if "resolution" in sections:
        progress("live: resolution ...")
        out["resolution"] = await resolution(api)
    if "truth" in sections:
        progress("live: truth (the adversarial scenarios, four conditions) ...")
        out["truth"] = await truth(api, reps)
    if "learning" in sections:
        progress("live: learning ...")
        out["learning"] = await learning(api)
    if "jev_model" in sections:
        progress("live: jev with the model ...")
        out["jev_model"] = await jev_with_model(api)
    if "email" in sections:
        progress("live: email ...")
        out["email"] = await email_bench(api)
    if TIMINGS:
        out["latency"] = {"turns": len(TIMINGS), "first_sound_ms": dist([t["first_sound"] for t in TIMINGS if t["first_sound"] is not None]),
                          "first_word_ms": dist([t["first_word"] for t in TIMINGS if t["first_word"] is not None]),
                          "full_reply_ms": dist([t["done"] for t in TIMINGS if t["done"] is not None])}
    if SERVER_TIMINGS:
        f = [t["filler"] for t in SERVER_TIMINGS if t["filler"] is not None]
        out["server_side"] = {"turns": len(SERVER_TIMINGS), "acknowledgement_ms": dist(f), "jev_ms": dist([t["jev"] for t in SERVER_TIMINGS if t["jev"] is not None]),
                              "first_word_ms": dist([t["first_word"] for t in SERVER_TIMINGS if t["first_word"] is not None]),
                              "turn_total_ms": dist([t["total"] for t in SERVER_TIMINGS if t["total"] is not None]),
                              "turns_with_acknowledgement": len(f) / len(SERVER_TIMINGS)}
    out["gpu"] = gpu()
    return out
