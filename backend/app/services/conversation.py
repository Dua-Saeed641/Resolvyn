"""The live conversation pipeline (docs/architecture.md §2.1-2.7, project.md §59, §62).

    caller speech
      → Perception     clean-up, language, entities
      → Jev            is the caller talking to me? intent, sentiment, urgency
      → Memory         Jev-written query → vector + knowledge graph (both memories)
      → Decision       instant-resolve | tools | first-time bug | escalate
      → Agent          department playbook runs tools → verified facts
      → Persona (LLM)  says it like a person, streamed sentence by sentence
      → Context engine ticket, summaries, timeline updated in the background

Everything the caller hears is emitted as `agent_sentence` events over the
session's WebSocket; the browser turns each into audio as soon as it arrives.
"""

import asyncio
import re
import time

from app.agents import orchestrator
from app.agents.base_agent import Plan, TurnContext
from app.agents.persona import build_messages
from app.config import get_settings
from app.context_engine import context_engine
from app.decision_engine.decision_engine import Decision, decide
from app.judgment import jev
from app.llm import LLMUnavailable, llm
from app.memory.memory_engine import memory
from app.perception import perception_service
from app.services import ticket_service as tickets
from app.services.realtime import hub
from app.services.sessions import CallSession, sessions
from app.voice import speech

MAX_REPLY_SENTENCES = 3
_background: set[asyncio.Task] = set()


def _spawn(coro) -> asyncio.Task:
    """Run follow-up work (summaries, context doc, memory) independently of the caller's turn.

    A turn can be cancelled at any moment (barge-in, hang-up); finalisation must never be.
    """
    task = asyncio.create_task(coro)
    _background.add(task)
    task.add_done_callback(_background.discard)
    return task
_SIDE_TAG = re.compile(r"^\s*\[?\s*SIDE[_ ]?TALK", re.I)
_PREFIX = re.compile(r"^\s*(?:riya|agent|assistant)\s*:\s*", re.I)


# ─────────────────────────────────────────────────────────────────────────────
# emit helpers
# ─────────────────────────────────────────────────────────────────────────────


def _emit(session: CallSession, event: dict) -> None:
    hub.to_session(session.session_id, event)


def _agent_status(session: CallSession, state: str) -> None:
    """listening | thinking | speaking | idle — drives the call screen indicator."""
    _emit(session, {"type": "agent_status", "state": state})


def _say(session: CallSession, text: str, turn: int, *, filler: bool = False, sender: str = "agent") -> None:
    _emit(session, {
        "type": "agent_sentence", "turn": turn, "text": text, "say": speech.to_spoken(text),
        "lang": session.language, "filler": filler, "sender": sender,
    })


# ─────────────────────────────────────────────────────────────────────────────
# call lifecycle
# ─────────────────────────────────────────────────────────────────────────────


async def start(session: CallSession) -> None:
    """Create the ticket and greet the caller (instant, no model needed)."""
    s = get_settings()
    cust = session.customer
    t = tickets.create(
        session.session_id, channel=session.channel, customer_id=cust["customer_id"] if cust else None,
        customer_name=cust["name"] if cust else None, language=session.language,
    )
    session.ticket_id = t.ticket_id
    if cust:
        session.state["customer_id"] = cust["customer_id"]
    name = cust["name"].split()[0] if cust else None
    if session.language == "hi":
        greeting = f"Namaste{' ' + name + ' ji' if name else ''}! Main {s.agent_name} bol rahi hoon, {s.business_name} se. Bataiye, main aapki kaise madad kar sakti hoon?"
    else:
        greeting = (f"Hi {name}! " if name else "Hi there! ") + f"This is {s.agent_name} from {s.business_name}. How can I help you today?"
    session.history.append({"role": "assistant", "content": greeting})
    tickets.add_message(t.ticket_id, "Resolvyn", greeting, kind=session.channel.lower() if session.channel == "Text" else "speech")
    _say(session, greeting, 0)
    _emit(session, {"type": "agent_done", "turn": 0})
    orchestrator.set_state("Other", "IDLE")


def submit(session: CallSession, text: str) -> None:
    """Entry point for a finished caller utterance. Barge-in: a new utterance cancels the old turn."""
    session.cancel_turn()
    if session.ticket_id:
        context_engine.cancel(session.ticket_id)  # the GPU belongs to the caller's reply now
    session.seq += 1
    seq = session.seq
    session.task = asyncio.create_task(_guard(session, text, seq))


def barge_in(session: CallSession) -> None:
    session.cancel_turn()
    _agent_status(session, "listening")


async def _guard(session: CallSession, text: str, seq: int) -> None:
    try:
        async with session.lock:
            await _turn(session, text, seq)
    except asyncio.CancelledError:
        raise
    except Exception as e:  # noqa: BLE001 - a bug must never leave the caller in silence
        print(f"[conversation] turn failed: {type(e).__name__}: {e}", flush=True)
        import traceback
        traceback.print_exc()
        if session.ticket_id:
            tickets.add_event(session.ticket_id, "Resolvyn", "ERROR", f"Turn failed: {type(e).__name__}", status="FAILED")
        _say(session, "Sorry, I lost my train of thought for a second. Could you say that again?", seq)
        _emit(session, {"type": "agent_done", "turn": seq})


# ─────────────────────────────────────────────────────────────────────────────
# one caller turn
# ─────────────────────────────────────────────────────────────────────────────


def _apply_entities(session: CallSession, ent: dict) -> None:
    st = session.state
    for k in ("order_id", "email", "phone_last4"):
        if ent.get(k):
            st[k] = ent[k]
    if ent.get("name") and not st.get("name"):
        st["name"] = ent["name"]
    if ent.get("order_id") and session.ticket_id:
        tickets.update(session.ticket_id, order_id=ent["order_id"])


def _choose_filler(session: CallSession, text: str, j: jev.Judgment, ent: dict) -> str | None:
    """A human acknowledgement said *before* the model has produced a word."""
    st = session.state
    words = len(text.split())
    if words <= 3 or j.done or st.get("awaiting") == "approval":
        return None
    if j.sentiment in ("Frustrated", "Angry") and not st.get("empathy_given"):
        st["empathy_given"] = True
        return "empathy"
    if ent.get("order_id") or (st.get("awaiting") in ("confirm_refund", "confirm_unlock", "confirm_cancel") and (j.yes or j.no)):
        return "checking"
    if words >= 8 and not st.get("acked_recently"):
        st["acked_recently"] = True
        return "ack"
    st["acked_recently"] = False
    return None


async def _turn(session: CallSession, raw: str, seq: int) -> None:
    started = time.perf_counter()
    st = session.state
    tid = session.ticket_id
    assert tid
    enriched = perception_service.enrich(raw, session.channel)
    text, ent = enriched["text"], enriched["entities"]
    if not text:
        return
    if enriched["language"] != session.language and len(text.split()) >= 3:
        session.language = enriched["language"]
        tickets.update(tid, language=session.language)

    # ── a person took over: record only, the AI stays quiet ──────────────────
    if session.human_active:
        tickets.add_message(tid, "CUSTOMER", text, kind="speech")
        session.history.append({"role": "user", "content": text})
        return

    # ── 1. is the caller talking to me at all? ───────────────────────────────
    who, why = jev.addressee(text, expecting_answer=bool(st.get("awaiting")))
    if who == "other":
        _record_side_talk(session, text, why)
        return

    _agent_status(session, "thinking")
    tickets.add_message(tid, "CUSTOMER", text, kind="speech")
    session.history.append({"role": "user", "content": text})
    _apply_entities(session, ent)
    ticket = tickets.get(tid)
    if ticket and ticket.status == "NEW":
        tickets.update(tid, status="ANALYZING")

    # ── 2. Jev ───────────────────────────────────────────────────────────────
    plan_name = session.customer.get("plan") if session.customer else None
    j = jev.rules_judge(text, session.prior_judgment, plan=plan_name)  # microseconds

    # immediate human acknowledgement, before any model has produced a word
    filler_text = None
    fk = _choose_filler(session, text, j, ent)
    if fk:
        filler_text = speech.pick_filler(fk, session.language)
        _say(session, filler_text, seq, filler=True)

    if jev.is_unsure(text, j):  # only now spend a model call on an unsure judgment
        j = await jev.refine_with_model(text, j, session.history[:-1])
    j.query = jev.write_query(text, j, subject=(ticket.subject if ticket and ticket.subject != "New conversation" else st.get("subject")))
    _note_judgment(session, ticket, j, ent, time.perf_counter() - started)

    # ── 3. memory: Jev-written query → both memories ─────────────────────────
    department = j.department
    orchestrator.set_state(department, "RETRIEVING", tid, "Retrieving knowledge and memory")
    ret = memory.retrieve(j.query, department, exclude_ticket=tid)
    _note_retrieval(session, ret, j)

    customer = session.customer
    ctx = TurnContext(session=session, ticket_id=tid, text=text, entities=ent, judgment=j, retrieval=ret,
                      customer=customer, state=st, language=session.language)

    # ── 4. resolution of the previous answer ("does that help?" → yes) ───────
    resolved_now = False
    if st.get("awaiting") == "confirm_helped" and (j.done or (j.yes and not j.no)):
        plan = Plan(goal="The caller is happy. Say a short warm goodbye and wish them a good day.",
                    fallback="Wonderful! Thanks for calling Nova Retail, have a lovely day.",
                    status="RESOLVED", agent_state="COMPLETED", operation="Resolved", use_knowledge=False)
        decision = Decision("INSTANT", "Caller confirmed", 95)
        resolved_now = True
    elif j.done and not st.get("awaiting") and st.get("problem_stated") and not st.get("bug_flagged") \
            and ticket and ticket.status in ("ACTIVE", "VERIFYING") and not ticket.needs_human:
        plan = Plan(goal="The caller says that's all. Say a short warm goodbye.",
                    fallback="Great, thanks for calling Nova Retail. Have a lovely day!",
                    status="RESOLVED", agent_state="COMPLETED", operation="Resolved", use_knowledge=False)
        decision = Decision("INSTANT", "Caller finished", 92)
        resolved_now = True
    else:
        if st.get("awaiting") == "confirm_helped":
            st["awaiting"] = None
        # ── 5. decision engine ───────────────────────────────────────────────
        decision = await decide(ctx)
        _note_decision(session, decision)

        # ── 6. the department agent (or the special paths) ───────────────────
        agent = orchestrator.route(department)
        if decision.small_talk:
            plan = Plan(goal="Warmly ask how you can help today.", fallback="Sure, I'm here. What can I help you with?",
                        agent_state="IDLE", operation="Waiting for caller", use_knowledge=False)
        elif decision.path == "ESCALATED":
            plan = _escalation_plan(ctx, decision.escalate_reason or "Escalated")
        elif decision.path in ("FIRST_TIME_BUG", "KNOWN_OPEN_BUG"):
            plan = await _first_time_bug(ctx, decision)
        else:
            st["problem_stated"] = True
            if not st.get("subject") and j.intent != "General Query":
                st["subject"] = text[:140]
            orchestrator.set_state(department, "ACTING", tid, f"{j.intent}")
            if decision.bug_suggestion:
                plan = Plan(goal="A teammate already solved this exact problem before. Explain the suggested fix in your own words, one or two steps, and ask them to try it.",
                            fallback=f"We've seen this before. Here's what worked: {decision.bug_suggestion}",
                            facts=[f"Suggested fix from a previous case: {decision.bug_suggestion}"], status="ACTIVE", path="INSTANT",
                            agent_state="COMPLETED", operation="Applying a fix learned from a past case")
                st["awaiting"] = "tech_feedback"
            else:
                plan = await agent.plan(ctx)
        customer = session.customer
        ctx.customer = customer

    # ── 7. apply the plan to the ticket / agent ──────────────────────────────
    await _apply_plan(session, ctx, plan, decision, j, agent_name=department)

    # ── 8. say it ────────────────────────────────────────────────────────────
    _agent_status(session, "thinking")
    reply = await _speak_plan(session, ctx, plan, decision, seq, already_said=filler_text)
    full = " ".join(x for x in (filler_text, reply) if x).strip()
    if reply is None:  # the model decided this was side talk after all
        _record_side_talk(session, text, "model judged it side talk", already_recorded=True)
        return
    if full:
        session.history.append({"role": "assistant", "content": full})
        session.last_agent_text = full
        tickets.add_message(tid, "Resolvyn", full, kind="speech")
    _emit(session, {"type": "agent_done", "turn": seq})

    # ── 9. after-speech bookkeeping ──────────────────────────────────────────
    if resolved_now or plan.status == "RESOLVED":
        await finalize_resolution(session, by="AI")
    else:
        orchestrator.set_state(department, "WAITING" if plan.agent_state == "WAITING" else "COMPLETED", tid, plan.operation or None)
        _schedule_nudge(session, seq)
    session.prior_judgment = j
    _spawn(context_engine.refresh(tid))
    print(f"[turn {seq}] {time.perf_counter() - started:.2f}s total path={decision.path} dept={department}", flush=True)


# ─────────────────────────────────────────────────────────────────────────────
# notes → ticket + timeline
# ─────────────────────────────────────────────────────────────────────────────


def _note_judgment(session: CallSession, ticket, j: jev.Judgment, ent: dict, took: float) -> None:
    tid = session.ticket_id
    st = session.state
    changed_dept = ticket is not None and ticket.assigned_agent != j.department
    fields = dict(intent=j.intent, sentiment=j.sentiment, urgency=j.urgency, priority=j.priority,
                  confidence=j.confidence)
    if changed_dept:
        fields["assigned_agent"] = j.department
        fields["status"] = "ROUTING"
    tickets.update(tid, **fields)
    tickets.add_event(
        tid, "Jev", "INTENT_DETECTED",
        f"Intent {j.intent} · sentiment {j.sentiment} · urgency {j.urgency} · confidence {j.confidence}%"
        + (" (carried over)" if j.carried else ""),
        status="COMPLETED", meta={"judgment": j.public(), "query": j.query, "ms": int(took * 1000)},
    )
    if changed_dept:
        prev = ticket.assigned_agent if ticket else None
        tickets.add_event(
            tid, "Orchestrator", "AGENT_ASSIGNED",
            f"{j.department} Agent assigned" + (f" (handed over from {prev} with full context)" if prev else ""),
            status="COMPLETED", public=f"Routed to our {j.department} team",
        )
        if prev:
            st["awaiting"] = None
            orchestrator.set_state(prev, "IDLE")
        tickets.update(tid, status="ACTIVE")
    if j.sentiment == "Angry":
        st["angry_streak"] = st.get("angry_streak", 0) + 1
    else:
        st["angry_streak"] = 0
    st["department"] = j.department


def _note_retrieval(session: CallSession, ret, j: jev.Judgment) -> None:
    tid = session.ticket_id
    sources = ret.sources()
    tickets.update(tid, knowledge=sources)
    if any(s["via"] == "graph" for s in sources):
        tickets.add_event(tid, "Memory", "MEMORY_RETRIEVED",
                          "Similar past cases recalled from the knowledge graph: "
                          + ", ".join(sorted({s["ref_ticket_id"] for s in sources if s["via"] == "graph" and s["ref_ticket_id"]})),
                          status="COMPLETED", meta={"sources": [s for s in sources if s["via"] == "graph"]})
    tickets.add_event(
        tid, "Memory", "KNOWLEDGE_RETRIEVED",
        f"Jev query → {len(sources)} sources · best match {ret.best_common:.2f} (rulebook) / {ret.best_bug:.2f} (first-time-bug memory)",
        status="COMPLETED", meta={"query": j.query, "sources": sources, "best_common": round(ret.best_common, 2), "best_bug": round(ret.best_bug, 2)},
    )


def _note_decision(session: CallSession, d: Decision) -> None:
    tickets.add_event(
        session.ticket_id, "Decision Engine", "DECISION",
        f"{d.path.replace('_', ' ').title()} — {d.reason}" + (f" ({d.note})" if d.note else ""),
        status="COMPLETED", meta={"path": d.path, "confidence": d.confidence},
    )


def _record_side_talk(session: CallSession, text: str, why: str, *, already_recorded: bool = False) -> None:
    """The caller is talking to someone else: stay silent, keep it out of the ticket."""
    tid = session.ticket_id
    if not already_recorded:
        tickets.add_message(tid, "CUSTOMER", text, kind="side_talk")
    tickets.add_event(tid, "Jev", "SIDE_TALK_DETECTED", f"Caller is talking to someone else — agent stays quiet ({why})",
                      status="COMPLETED", meta={"text": text})
    _emit(session, {"type": "side_talk", "text": text, "reason": why})
    _agent_status(session, "listening")
    if session.nudge and not session.nudge.done():
        session.nudge.cancel()
    session.nudge = asyncio.create_task(_nudge(session, "nudge_side", 14.0))


# ─────────────────────────────────────────────────────────────────────────────
# special paths: escalation and first-time bug
# ─────────────────────────────────────────────────────────────────────────────

TEAM = {"Billing": "Ananya Rao", "Account": "Vikram Shah", "Order": "Meera Iyer", "Technical": "Arjun Menon", "Other": "Sana Khan"}


def _escalation_plan(ctx: TurnContext, reason: str) -> Plan:
    st = ctx.state
    missing = []
    if not (ctx.customer or st.get("name")):
        missing.append("your name")
    if not st.get("order_id") and ctx.judgment.department in ("Billing", "Order"):
        missing.append("your order ID")
    ask = f" Could you tell me {' and '.join(missing)} so they have it ready?" if missing else ""
    return Plan(
        goal=f"Tell the caller you're bringing in a teammate right now, that they'll already have the full conversation so the caller won't repeat themselves.{ask}",
        fallback="Of course. I'm bringing in a teammate right now, and they'll have everything we've discussed." + ask,
        status="WAITING_FOR_HUMAN", path="ESCALATED", agent_state="WAITING", operation="Escalated to the team",
        escalate=reason, use_knowledge=False, next_step="Team member to pick up with the full context",
    )


async def _first_time_bug(ctx: TurnContext, d: Decision) -> Plan:
    st, tid, j = ctx.state, ctx.ticket_id, ctx.judgment
    department = j.department
    if d.path == "KNOWN_OPEN_BUG":
        tickets.update(tid, needs_human=True, status="WAITING_FOR_HUMAN", resolution_path="ESCALATED",
                       escalation_reason="Same unknown problem is already open with the team")
        st["awaiting"] = None
        return Plan(
            goal="This exact problem has already been reported and the team is working on it. Say that honestly, that you've added their case to it, and thank them for their patience.",
            fallback="This looks like a problem our team is already working on, so I've added your case to it. Thanks for your patience.",
            status="WAITING_FOR_HUMAN", path="ESCALATED", agent_state="WAITING", operation="Linked to an open problem",
            escalate="Same unknown problem is already open with the team", use_knowledge=False,
        )

    if not st.get("bug_flagged"):
        ticket = tickets.get(tid)
        subject = (ticket.subject if ticket and ticket.subject != "New conversation" else "") or ctx.text
        title = _clip(re.sub(r"\s+", " ", ctx.text), 100)
        detail = " ".join(m["content"] for m in ctx.session.history if m["role"] == "user")[-700:]
        st["subject"] = st.get("subject") or subject[:140]
        bug = memory.record_first_time_bug(tid, title, detail, department)
        st.update(bug_flagged=True, bug_id=bug.bug_id, awaiting="bug_followup", problem_stated=True)
        tickets.update(tid, is_first_time_bug=True, needs_human=True, status="WAITING_FOR_HUMAN", resolution_path="FIRST_TIME_BUG",
                       escalation_reason="First-time bug: no precedent in memory", subject=st["subject"][:120],
                       next_step="Manager to enter a suggestion for the AI")
        tickets.add_event(tid, "Decision Engine", "FIRST_TIME_BUG_FLAGGED",
                          "A FIRST TIME BUG HAS BEEN REPORTED — no precedent in either memory",
                          status="WAITING", meta={"bug_id": bug.bug_id}, public="Escalated to a specialist")
        hub.to_ops({"type": "bug_alert", "bug": tickets.bug_dict(bug),
                    "ticket": tickets.summary(tickets.get(tid)),
                    "banner": "A FIRST TIME BUG HAS BEEN REPORTED — HERE'S MORE DETAIL, PLEASE ENTER YOUR SUGGESTION"})
        return Plan(
            goal="Be honest and natural: this is a new one for you, you've flagged it to your team lead right now and they'll suggest a fix while the caller is on the line. Ask ONE useful detail (like the model, when it started, or what they already tried). Do not offer any fix yet.",
            fallback="Hmm, that's a new one for me. I've flagged it to my team lead right now, and they'll suggest a fix while you're on the line. When did this start?",
            status="WAITING_FOR_HUMAN", path="FIRST_TIME_BUG", agent_state="WAITING", operation="First-time bug — waiting for team suggestion",
            escalate=None, use_knowledge=False, next_step="Manager to enter a suggestion for the AI",
        )

    # follow-up while we wait for the manager's suggestion
    from sqlmodel import Session

    from app.database import engine
    from app.models import FirstTimeBug

    with Session(engine) as s:
        b = s.get(FirstTimeBug, st.get("bug_id"))
        if b:
            b.detail = (b.detail + " | caller: " + ctx.text)[-1200:]
            s.add(b)
            s.commit()
    return Plan(
        goal="Thank them for the extra detail, say you've added it for your team lead and you're waiting for their suggestion. Keep them company in one short sentence. Do not offer any fix.",
        fallback="Thanks, that helps. I've added it for my team lead, and I'm just waiting for their suggestion. Please bear with me.",
        status="WAITING_FOR_HUMAN", path="FIRST_TIME_BUG", agent_state="WAITING", operation="Waiting for team suggestion",
        use_knowledge=False,
    )


# ─────────────────────────────────────────────────────────────────────────────
# apply plan → ticket
# ─────────────────────────────────────────────────────────────────────────────


async def _apply_plan(session: CallSession, ctx: TurnContext, plan: Plan, decision: Decision, j: jev.Judgment, *, agent_name: str) -> None:
    tid = session.ticket_id
    fields: dict = {}
    if plan.status and plan.status != "RESOLVED":
        fields["status"] = plan.status
    if plan.path:
        fields["resolution_path"] = plan.path
    elif decision.path in ("INSTANT", "ACTION") and not (tickets.get(tid) and tickets.get(tid).resolution_path)             and plan.status != "RESOLVED":
        fields["resolution_path"] = decision.path
    if plan.next_step:
        fields["next_step"] = plan.next_step
    st = session.state
    conf = _confidence(j, decision, plan)
    fields["confidence"] = conf
    if session.customer:
        fields.setdefault("customer_name", session.customer["name"])
    elif st.get("name"):
        fields["customer_name"] = st["name"]
    if fields:
        tickets.update(tid, **fields)
    if plan.escalate:
        await escalate(session, plan.escalate)
    orchestrator.set_state(agent_name, plan.agent_state if plan.agent_state != "COMPLETED" else "ACTING", tid, plan.operation or None)
    tickets.add_event(tid, agent_name, "RESPONSE_GENERATED", plan.operation or "Response prepared", status="COMPLETED",
                      meta={"goal": plan.goal, "facts": plan.facts})


def _confidence(j: jev.Judgment, d: Decision, plan: Plan) -> int:
    base = j.confidence
    if d.path == "ACTION":
        base = max(base, int(d.confidence))
        if any("VERIFIED" in f for f in plan.facts):
            base += 6
    elif d.path in ("INSTANT", "FIRST_TIME_BUG", "KNOWN_OPEN_BUG"):
        base = int(0.45 * j.confidence + 0.55 * min(100, d.confidence))
        if d.path == "FIRST_TIME_BUG":
            base = min(base, 58)
    return max(30, min(99, base))


async def escalate(session: CallSession, reason: str) -> None:
    """Escalate in real time, before the call ends (docs/architecture.md §2.2)."""
    tid = session.ticket_id
    t = tickets.get(tid)
    if t and t.escalated and t.escalation_reason == reason:
        return
    dept = session.state.get("department") or (t.assigned_agent if t else None) or "Other"
    assignee = f"{TEAM.get(dept, 'Sana Khan')} ({dept} team)"
    tickets.update(tid, escalated=True, needs_human=True, escalation_reason=reason, assignee=assignee,
                   status="WAITING_FOR_HUMAN", resolution_path=(t.resolution_path if t and t.resolution_path == "FIRST_TIME_BUG" else "ESCALATED"))
    tickets.add_event(tid, "Orchestrator", "ESCALATED", f"Escalated to {assignee}: {reason}", status="WAITING",
                      public=f"Escalated to our {dept} team")
    _spawn(context_engine.on_escalation(tid))  # the caller hears the reply first


# ─────────────────────────────────────────────────────────────────────────────
# speaking
# ─────────────────────────────────────────────────────────────────────────────


def _clip(text: str, n: int) -> str:
    """Shorten at a word boundary (never mid-word)."""
    if len(text) <= n:
        return text
    return text[:n].rsplit(" ", 1)[0].rstrip(",.;:- ") + "…"


def _clean(sentence: str) -> str:
    s = _PREFIX.sub("", sentence).strip().strip('"').strip()
    return s


async def _speak_plan(session: CallSession, ctx: TurnContext, plan: Plan, decision: Decision | None, seq: int, *,
                      already_said: str | None, proactive: bool = False) -> str | None:
    """Stream the model's words as sentences. Returns the spoken text, or None for side talk."""
    agent = orchestrator.route(ctx.judgment.department if ctx.judgment else "Other")
    if not llm.ready("fast"):
        return _fallback(session, plan, seq)

    messages = build_messages(ctx, plan, decision, history=session.history, already_said=already_said,
                              guidance=session.guidance, proactive=proactive, department_persona=agent.persona)
    streamer = speech.SentenceStreamer()
    spoken: list[str] = []
    held = ""  # a very short opener ("Okay.", "Got it.") waits for the next sentence so the voice does not stutter
    queued: list[str] = []  # everything after the first sentence is spoken as ONE chunk (fewer TTS calls, smoother voice)
    limit = 2 if plan.status == "RESOLVED" else MAX_REPLY_SENTENCES
    head = ""
    checked = False

    def speak(sentence: str) -> None:
        if not spoken:
            _say(session, sentence, seq)  # the first sentence goes out at once
        else:
            queued.append(sentence)
        spoken.append(sentence)

    def flush_queue() -> None:
        if queued:
            _say(session, " ".join(queued), seq)
            queued.clear()

    def emit(raw: str, *, final: bool = False) -> None:
        nonlocal held
        sentence = speech.humanize(_clean(raw))
        if not sentence or _redundant_ack(sentence, spoken, already_said):
            return
        if held:
            sentence, held = f"{held} {sentence}", ""
        if not final and len(sentence.split()) <= 3 and sentence[-1] in ".!,?":
            held = sentence
            return
        speak(sentence)

    try:
        async for piece in llm.stream(messages, tier="fast", max_tokens=100, temperature=0.85):
            if not checked:
                head += piece
                if len(head) < 14 and "]" not in head:
                    continue
                checked = True
                if _SIDE_TAG.match(head):
                    return None
                piece, head = head, ""
            for sentence in streamer.feed(piece):
                emit(sentence)
            if len(spoken) >= limit:
                break
        if not checked and head:
            if _SIDE_TAG.match(head):
                return None
            for sentence in streamer.feed(head):
                emit(sentence)
        tail = streamer.flush() if len(spoken) < limit else None
        if tail:
            emit(tail, final=True)
        if held:
            speak(held)
            held = ""
        flush_queue()
    except LLMUnavailable:
        flush_queue()
        if not spoken:
            return _fallback(session, plan, seq)
    except asyncio.CancelledError:
        # barge-in: keep what was already generated in the transcript
        if spoken:
            session.history.append({"role": "assistant", "content": " ".join(spoken)})
        raise
    if not spoken:
        return _fallback(session, plan, seq)
    # A one-word reaction ("Sure, why not.") that skips the actual point is worse than silence:
    # add the playbook's own line so the caller always hears what matters.
    if len(" ".join(spoken).split()) < 6 and plan.status != "RESOLVED" and (plan.facts or plan.escalate or plan.status):
        line = speech.humanize(plan.fallback)
        _say(session, line, seq)
        spoken.append(line)
    return " ".join(spoken)


_ACKS = {"got it", "okay", "ok", "sure", "sure yeah", "right", "yeah", "alright", "mm-hmm", "mm hmm", "i see", "okay got it", "understood"}


def _redundant_ack(sentence: str, spoken: list[str], already_said: str | None) -> bool:
    """A bare 'Got it.' straight after a filler acknowledgement sounds like a stutter."""
    if spoken or not already_said:
        return False
    plain = re.sub(r"[^a-z\- ]", "", sentence.lower()).strip()
    return plain in _ACKS


def _fallback(session: CallSession, plan: Plan, seq: int) -> str:
    line = speech.humanize(plan.fallback)
    _say(session, line, seq)
    return line


def _schedule_nudge(session: CallSession, seq: int) -> None:
    st = session.state
    if session.closed or session.channel != "Call":
        return
    if st.get("awaiting") in ("approval", "bug_followup") or not st.get("awaiting"):
        return
    if session.nudge and not session.nudge.done():
        session.nudge.cancel()
    session.nudge = asyncio.create_task(_nudge(session, "nudge_silence", 22.0))


async def _nudge(session: CallSession, kind: str, delay: float) -> None:
    try:
        await asyncio.sleep(delay)
        if session.closed or session.human_active:
            return
        text = speech.pick_filler(kind, session.language)
        session.seq += 1
        _say(session, text, session.seq, filler=True)
        _emit(session, {"type": "agent_done", "turn": session.seq})
        tickets.add_message(session.ticket_id, "Resolvyn", text, kind="speech")
        session.history.append({"role": "assistant", "content": text})
    except asyncio.CancelledError:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# out-of-band events: human approval / suggestion → the AI speaks proactively
# ─────────────────────────────────────────────────────────────────────────────


async def resume(ticket_id: str, event: str, payload: dict) -> None:
    """A human acted (approved a refund, gave a first-time-bug suggestion). Continue the call."""
    session = sessions.by_ticket(ticket_id)
    if session is None or session.human_active:
        return
    # Never cut off what the AI is saying: wait for the current turn, then continue.
    async with session.lock:
        session.seq += 1
        seq = session.seq
        st = session.state
        j = session.prior_judgment or jev.Judgment()
        dept = st.get("department") or j.department
        agent = orchestrator.route(dept)
        ctx = TurnContext(session=session, ticket_id=ticket_id, text="", entities={}, judgment=j, retrieval=None,
                          customer=session.customer, state=st, language=session.language)
        orchestrator.set_state(dept, "ACTING", ticket_id, f"Resuming after human {event}")
        plan = await agent.resume(ctx, event, payload)
        if event == "suggestion":
            st["bug_suggestion_given"] = True
        await _apply_plan(session, ctx, plan, Decision("ACTION", f"Human {event}", 90), j, agent_name=dept)
        filler_text = None
        if plan.filler and not session.closed and session.channel == "Call":
            filler_text = speech.pick_filler(plan.filler, session.language)
            _say(session, filler_text, seq, filler=True)
        reply = await _speak_plan(session, ctx, plan, None, seq, already_said=filler_text, proactive=True)
        full = " ".join(x for x in (filler_text, reply) if x).strip()
        if full:
            session.history.append({"role": "assistant", "content": full})
            tickets.add_message(ticket_id, "Resolvyn", full, kind="speech")
        _emit(session, {"type": "agent_done", "turn": seq})
        if plan.status == "RESOLVED":
            await finalize_resolution(session, by="AI")
        else:
            orchestrator.set_state(dept, "WAITING" if plan.agent_state == "WAITING" else "COMPLETED", ticket_id, plan.operation or None)
            if session.closed and plan.status == "VERIFYING":
                # the caller already hung up: the verified result is on their ticket
                await finalize_resolution(session, by="AI")
            else:
                _schedule_nudge(session, seq)
        _spawn(context_engine.refresh(ticket_id))


# ─────────────────────────────────────────────────────────────────────────────
# resolution + end of call
# ─────────────────────────────────────────────────────────────────────────────


async def finalize_resolution(session: CallSession, *, by: str = "AI") -> None:
    tid = session.ticket_id
    t = tickets.get(tid)
    if not t or t.status == "RESOLVED":
        return
    tickets.update(tid, status="RESOLVED", handled_by=by, needs_human=False if by == "AI" else t.needs_human)
    tickets.add_event(tid, t.assigned_agent or "Resolvyn", "TICKET_RESOLVED",
                      f"Ticket resolved by {'the AI' if by == 'AI' else 'a team member'}", status="COMPLETED",
                      public="Resolved")
    if t.assigned_agent:
        orchestrator.set_state(t.assigned_agent, "IDLE")
        orchestrator.mark_resolved(t.assigned_agent)
    session.state["awaiting"] = None
    _spawn(context_engine.on_resolution(tid, by))


async def end_call(session: CallSession, reason: str = "hangup") -> None:
    """The caller hung up (or the tab closed). Never leave a ticket in limbo."""
    if session.closed:
        return
    session.cancel_turn()
    session.closed = True
    tid = session.ticket_id
    if not tid:
        return
    t = tickets.get(tid)
    tickets.update(tid, call_active=False)
    tickets.add_event(tid, "Resolvyn", "CALL_ENDED", f"Call ended ({reason})", status="COMPLETED")
    if not t or t.status in ("RESOLVED", "FAILED"):
        return
    st = session.state
    if t.needs_human or st.get("awaiting") in ("approval", "bug_followup"):
        return  # stays with the team; the context doc explains where it stands
    if st.get("awaiting") == "confirm_helped" or (t.status == "VERIFYING"):
        await finalize_resolution(session, by="AI")
        return
    if st.get("problem_stated"):
        await escalate(session, "Call ended before the issue was resolved")
    else:
        tickets.update(tid, status="RESOLVED", subject="Call ended without a request", one_line_summary="Caller hung up before stating an issue.")
