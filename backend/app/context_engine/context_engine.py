"""Context engine — docs/architecture.md §2.5 (resolvyn-ai-loop-detail.png).

"Real-time extraction from the user conversation" into the structured ticket:
ticket id, customer name, body, AI confidence, plus the *one-line summary* and
the *detailed summary* the team reads. The summary is rewritten after every turn
while the call is still going, so a human who opens the ticket mid-call sees
exactly where the AI is. When the call ends, an optional deep pass by the 27B
model (epsilon "deep" tier) writes a longer analysis in the background.
"""

import asyncio

from app.config import get_settings
from app.integrations import jira_sim
from app.learning import learning_service
from app.llm import LLMUnavailable, llm
from app.memory.memory_engine import memory
from app.services import ticket_service as tickets
from app.services.realtime import hub

_tasks: dict[str, asyncio.Task] = {}

_SCHEMA = {
    "type": "object",
    "properties": {
        "customer_name": {"type": "string"},
        "subject": {"type": "string"},
        "one_line": {"type": "string"},
        "detailed": {"type": "string"},
        "next_step": {"type": "string"},
    },
    "required": ["customer_name", "subject", "one_line", "detailed", "next_step"],
}

_SYSTEM = (
    "You write the live case notes for a customer-support ticket that a human team member will read to take over. "
    "Be factual and specific; use only what is in the conversation and the verified actions. "
    "customer_name: the caller's name or empty string. subject: max 12 words describing the caller's problem. "
    "one_line: one sentence, max 22 words, of the situation right now. "
    "detailed: 3 to 5 sentences: what the caller wants, what the AI checked or did (and whether verified), "
    "what is still pending, and the caller's mood. next_step: the single next action, max 14 words. JSON only."
)


def _transcript(ticket_id: str, limit: int = 14) -> str:
    lines = []
    for m in tickets.messages(ticket_id)[-limit:]:
        who = "Caller" if m["sender"] == "CUSTOMER" else ("Team member" if m["sender"] == "HUMAN" else "Agent")
        lines.append(f"{who}: {m['content']}")
    return "\n".join(lines)


def _verified_facts(ticket_id: str) -> list[str]:
    facts: list[str] = []
    for e in reversed(tickets.events(ticket_id)):
        if e["event_type"] == "RESPONSE_GENERATED" and e["meta"].get("facts"):
            facts = e["meta"]["facts"]
            break
    return facts


def _heuristic(t, ticket_id: str) -> dict:
    caller = t.customer_name or "The caller"
    msgs = [m for m in tickets.messages(ticket_id) if m["sender"] == "CUSTOMER"]
    first = msgs[0]["content"] if msgs else "has not stated an issue yet"
    facts = _verified_facts(ticket_id)
    dept = t.assigned_agent or "unassigned"
    one = f"{t.intent or 'New request'}: {first[:110]}".rstrip(".")
    parts = [f"{caller} contacted support by {t.channel.lower()} and said: \"{first[:200]}\"."]
    parts.append(f"Handled by the {dept} Agent; sentiment {t.sentiment or 'unknown'}, confidence {t.confidence or 0}%.")
    if facts:
        parts.append("Verified so far: " + "; ".join(facts[:4]) + ".")
    parts.append(f"Current status: {t.status.replace('_', ' ').lower()}.")
    return {"one_line": one, "detailed": " ".join(parts), "next_step": t.next_step or "", "subject": first[:80],
            "customer_name": t.customer_name or ""}


def cancel(ticket_id: str) -> None:
    """Stop an in-flight background summary (a new caller utterance needs the model first)."""
    t = _tasks.get(ticket_id)
    if t and not t.done():
        t.cancel()


async def refresh(ticket_id: str, *, wait: bool = False) -> None:
    """Rewrite the ticket's live summary from the latest state.

    Background (default): a fresh pass replaces any older one, and is cancelled if the
    caller speaks again. wait=True runs inline and cannot be cancelled by that — used at
    escalation/resolution so the context doc never carries a stale summary.
    """
    cancel(ticket_id)
    if wait:
        await _refresh_once(ticket_id, delay=0)
        return
    task = asyncio.create_task(_refresh_once(ticket_id))
    _tasks[ticket_id] = task
    try:
        await task
    except asyncio.CancelledError:
        if not task.cancelled():
            raise  # we were cancelled ourselves, not the summary


def _publish(ticket_id: str, t, data: dict) -> dict:
    """Write the case notes to the ticket and push them to the team's screen."""
    fields = {"one_line_summary": data["one_line"][:220], "detailed_summary": data["detailed"]}
    if t.subject in ("New conversation", "", None) and data.get("subject"):
        fields["subject"] = data["subject"][:120]
    if not t.customer_name and data.get("customer_name"):
        fields["customer_name"] = data["customer_name"][:60]
    if data.get("next_step") and t.status not in ("RESOLVED",):
        fields["next_step"] = data["next_step"][:160]
    if t.status == "RESOLVED":
        fields["next_step"] = None
    tickets.update(ticket_id, **fields)
    hub.to_ops({"type": "summary", "ticket_id": ticket_id, "one_line_summary": fields["one_line_summary"],
                "detailed_summary": fields["detailed_summary"], "next_step": fields.get("next_step")})
    return fields


async def _refresh_once(ticket_id: str, delay: float = 1.0) -> None:
    t = tickets.get(ticket_id)
    if not t:
        return
    # 1. Instant baseline from the verified state: the notes are never blank, even when the
    #    caller talks fast enough to keep cancelling the model-written version below.
    data = _heuristic(t, ticket_id)
    _publish(ticket_id, t, data)

    if not (llm.ready("fast") and tickets.messages(ticket_id)):
        return
    # 2. Model-written notes, after a short debounce (a quick reply from the caller cancels this
    #    before it touches the GPU, so it never slows the conversation).
    if delay:
        await asyncio.sleep(delay)
    t = tickets.get(ticket_id) or t
    facts = _verified_facts(ticket_id)
    user = (
        f"Ticket {ticket_id} · department {t.assigned_agent} · status {t.status} · sentiment {t.sentiment}\n"
        f"Verified facts: {'; '.join(facts) if facts else 'none yet'}\n"
        f"Pending: {t.next_step or 'none'}\n\nConversation:\n{_transcript(ticket_id)}"
    )
    try:
        out = await asyncio.wait_for(
            llm.complete_json([{"role": "system", "content": _SYSTEM}, {"role": "user", "content": user}], _SCHEMA,
                              tier="fast", max_tokens=220, temperature=0.2),
            timeout=25,
        )
    except (LLMUnavailable, asyncio.TimeoutError, Exception):  # noqa: BLE001
        return  # keep the baseline
    for k in ("one_line", "detailed", "next_step", "subject", "customer_name"):
        if isinstance(out.get(k), str) and out[k].strip():
            data[k] = out[k].strip()
    _publish(ticket_id, tickets.get(ticket_id) or t, data)


# ── documents / Jira ─────────────────────────────────────────────────────────


def build_context_doc(ticket_id: str) -> str:
    d = tickets.detail(ticket_id)
    if not d:
        return ""
    lines = [
        f"# {d['ticket_id']} — {d['subject']}",
        "",
        "> Context document created autonomously by Resolvyn (simulated Confluence page).",
        "",
        f"| Field | Value |\n|---|---|\n| Customer | {d['customer_name'] or 'Unknown'} |\n| Channel | {d['channel']} |\n"
        f"| Department | {d['assigned_agent'] or '—'} |\n| Priority | {d['priority']} |\n| Status | {d['status']} |\n"
        f"| Sentiment | {d['sentiment'] or '—'} |\n| AI confidence | {d['confidence'] or 0}% |\n"
        f"| Assignee | {d['assignee'] or 'Unassigned'} |\n| Escalation reason | {d['escalation_reason'] or '—'} |",
        "",
        "## Summary",
        d["one_line_summary"] or "—",
        "",
        d["detailed_summary"] or "",
        "",
        "## Next step",
        d["next_step"] or "—",
        "",
        "## What the AI did",
    ]
    for e in d["events"]:
        if e["event_type"] in ("INTENT_DETECTED", "AGENT_ASSIGNED", "DECISION", "ACTION_PROPOSED", "ACTION_APPROVED",
                               "ACTION_EXECUTED", "ACTION_VERIFIED", "FIRST_TIME_BUG_FLAGGED", "ESCALATED", "HUMAN_GUIDANCE"):
            lines.append(f"- {e['timestamp'][11:19]} · {e['description']}")
    if d["tool_calls"]:
        lines += ["", "## Tool calls (simulated enterprise APIs)"]
        for c in d["tool_calls"]:
            lines.append(f"- `{c['tool_name']}` → {c['status']}")
    if d["knowledge"]:
        lines += ["", "## Knowledge used"]
        for k in d["knowledge"][:5]:
            lines.append(f"- {k['title']} ({k['store']}, score {k['score']})")
    if d["pending_actions"]:
        lines += ["", "## Approvals"]
        for p in d["pending_actions"]:
            lines.append(f"- {p['summary']} — {p['status']}")
    lines += ["", "## Conversation"]
    for m in d["messages"][-24:]:
        if m["kind"] == "side_talk":
            continue
        lines.append(f"- **{m['sender']}**: {m['content']}")
    return "\n".join(lines)


async def on_escalation(ticket_id: str) -> None:
    await refresh(ticket_id, wait=True)
    doc = build_context_doc(ticket_id)
    tickets.update(ticket_id, context_doc=doc)
    tickets.add_event(ticket_id, "Context Engine", "CONTEXT_DOC_CREATED",
                      "Context document created (simulated Confluence) and assigned to the team", status="COMPLETED")
    jira_sim.sync(ticket_id, reason="escalation")
    _email_summary(ticket_id, "escalated")
    asyncio.create_task(deep_summary(ticket_id))


async def on_resolution(ticket_id: str, by: str) -> None:
    await refresh(ticket_id, wait=True)
    t = tickets.get(ticket_id)
    if not t:
        return
    doc = build_context_doc(ticket_id)
    tickets.update(ticket_id, context_doc=doc)
    jira_sim.sync(ticket_id, reason="resolution")
    resolution = t.detailed_summary or t.one_line_summary or "Resolved."
    facts = _verified_facts(ticket_id)
    if facts:
        resolution = "; ".join(facts[:3]) + ". " + resolution
    d = tickets.detail(ticket_id) or {}
    memory.remember_ticket(
        {"ticket_id": ticket_id, "customer_id": t.customer_id, "subject": t.subject, "intent": t.intent,
         "assigned_agent": t.assigned_agent, "knowledge": d.get("knowledge", [])},
        resolution,
    )
    tickets.add_event(ticket_id, "Memory", "MEMORY_RETRIEVED", "Solved query added to episodic memory and the knowledge graph",
                      status="COMPLETED")
    learning_service.record(
        ticket_id, "Successful resolution", source_event="TICKET_RESOLVED",
        expected="Resolve without regressions", observed=f"Resolved by {'AI' if by == 'AI' else 'a team member'}",
        description=f"{t.intent or 'Query'} resolved" + (" with a human in the loop" if (t.escalated or t.needs_human or by != "AI") else " autonomously"),
    )
    _email_summary(ticket_id, "resolved")
    asyncio.create_task(deep_summary(ticket_id))


def _email_summary(ticket_id: str, kind: str) -> None:
    from app.services import email_service  # imported late: it depends on the conversation module

    try:
        email_service.send_summary(ticket_id, kind)
    except Exception as e:  # noqa: BLE001 - an email problem must never disturb the ticket
        print(f"[email] summary failed: {type(e).__name__}: {e}", flush=True)


_deep_queue: list[str] = []
_deep_worker: asyncio.Task | None = None


async def deep_summary(ticket_id: str) -> None:
    """Queue a fuller analysis by Qwen3.8-27B (epsilon deep tier) for when the machine is free."""
    global _deep_worker
    s = get_settings()
    if not s.deep_summaries or not llm.engine.available("deep"):
        return
    if ticket_id not in _deep_queue:
        _deep_queue.append(ticket_id)
    if _deep_worker is None or _deep_worker.done():
        _deep_worker = asyncio.create_task(_deep_loop())


async def _deep_loop() -> None:
    from app.services.sessions import sessions

    while _deep_queue:
        # The 27B saturates the CPU: only start after the line has been quiet for a while.
        quiet = 0
        while quiet < 15:
            await asyncio.sleep(1)
            quiet = quiet + 1 if sessions.active_calls() == 0 else 0
        ticket_id = _deep_queue[0]
        done = await _deep_once(ticket_id)
        if done:
            _deep_queue.pop(0)


async def _deep_once(ticket_id: str) -> bool:
    """Run one deep summary. Returns False if a live call interrupted it (job stays queued)."""
    from app.services.sessions import sessions

    t = tickets.get(ticket_id)
    if not t:
        return True
    prompt = [
        {"role": "system", "content": "You are a senior support analyst. Write a concise analysis (5 to 7 sentences, plain prose) "
         "for the team: the customer's problem, the root cause if known, what was done and verified, what remains, "
         "and one recommendation to prevent it happening again. Use only the information given."},
        {"role": "user", "content": f"Ticket {ticket_id} ({t.intent}, {t.assigned_agent} dept, status {t.status}).\n"
         f"Verified facts: {'; '.join(_verified_facts(ticket_id)) or 'none'}\n\nConversation:\n{_transcript(ticket_id, 24)}"},
    ]
    gen = asyncio.create_task(llm.complete(prompt, tier="deep", max_tokens=300, temperature=0.3))
    while not gen.done():
        await asyncio.wait({gen}, timeout=1)
        if not gen.done() and sessions.active_calls() > 0:
            gen.cancel()  # a caller is here: free the CPU and the ~9 GB of RAM right now
            try:
                await llm.engine.manager.stop_tier("deep")
            except Exception:  # noqa: BLE001
                pass
            return False
    try:
        text = gen.result()
    except (LLMUnavailable, Exception):  # noqa: BLE001
        return True
    if text.strip():
        tickets.update(ticket_id, deep_summary=text.strip())
        tickets.add_event(ticket_id, "Context Engine", "SUMMARY_UPDATED",
                          "Deep analysis written by Qwen3.8-27B (epsilon deep tier)", status="COMPLETED")
        hub.to_ops({"type": "summary", "ticket_id": ticket_id, "deep_summary": text.strip()})
    return True


