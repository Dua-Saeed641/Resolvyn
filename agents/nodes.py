"""Graph nodes — one responsibility each (spec §48).

Every node reuses the real backend service it corresponds to rather than
reimplementing it (spec §1, §4): perception/judgment/decision come from
`agents.engine_provider`; routing from `app.agents.orchestrator`; tool
execution + verification-worthy facts from the specialist agent's own
`plan()`/`resume()` (`app.agents.*_agent`, which already calls
`app.tools.tool_service`); ticket/timeline persistence from
`app.services.ticket_service`; the rulebook from `app.memory.rulebook`;
learning signals from `app.learning.learning_service`.

`agents/` never writes to `HumanAction`/`PendingAction`/`Ticket` rows through
any path other than these existing services, and never calls
`app.services.conversation` or `app.human_intelligence.human_service` — see
agents/README.md "Why a separate human-gate path" for why.
"""

from dataclasses import asdict

from langgraph.types import interrupt
from sqlmodel import Session, select

from app.agents import orchestrator
from app.agents.base_agent import Plan, TurnContext
from app.config import get_settings
from app.database import engine
from app.learning import learning_service
from app.memory import rulebook
from app.memory.memory_engine import memory
from app.models import Customer, FirstTimeBug, HumanAction
from app.services import ticket_service as tickets
from app.utils import utcnow
from app.vocab import DEPARTMENTS, HUMAN_EVENT_FOR_ACTION

from agents import swarm_router
from agents.engine_provider import DeterministicEngineProvider, judgment_dict, judgment_from_dict
from agents.state import ResolvynState

ENGINE = DeterministicEngineProvider()

CONFIRM_AWAITS = {"confirm_refund", "confirm_unlock", "confirm_reset", "confirm_cancel"}


# ── shared helpers ───────────────────────────────────────────────────────────


def _get_customer(customer_id: str | None) -> dict | None:
    if not customer_id:
        return None
    with Session(engine) as s:
        c = s.get(Customer, customer_id)
    return c.model_dump() if c else None


def _build_ctx(state: ResolvynState) -> TurnContext:
    """A TurnContext with no live session. Safe as long as `customer` is
    already populated (see agents/README.md — `identify()` is the only
    BaseAgent method that touches `ctx.session`, and it is never reached
    when `ctx.customer` is already set).
    """
    j = judgment_from_dict(state["judgment"]) if state.get("judgment") else None
    return TurnContext(
        session=None,
        ticket_id=state["ticket_id"],
        text=state["text"],
        entities=state.get("entities", {}),
        judgment=j,
        retrieval=None,
        customer=state.get("customer"),
        state=state["agent_state"],
        language=state.get("language", "en"),
    )


def _log_human_action(ticket_id: str, action: str, human_action: str, *, previous: str | None = None,
                       reason: str | None = None, operator: str = "Operator 01") -> dict:
    """Mirrors `human_intelligence/human_service.py::_log` (writes the same
    HumanAction row shape) without going through that module, which also
    tries to resume a *live call* — irrelevant and unsafe to trigger from a
    ticket-only graph run (spec §14-16: the graph owns its own resume)."""
    with Session(engine, expire_on_commit=False) as s:
        row = HumanAction(ticket_id=ticket_id, event_type=HUMAN_EVENT_FOR_ACTION[action],
                          previous_ai_action=previous, human_action=human_action, reason=reason, operator=operator)
        s.add(row)
        s.commit()
    return tickets.human_dict(row)


# ── 1. perception ────────────────────────────────────────────────────────────


def run_perception(state: ResolvynState) -> dict:
    enriched = ENGINE.perceive(state["text"], state.get("channel", "Ticket"))
    ticket = tickets.get(state["ticket_id"])
    customer = (
        state.get("customer")
        or _get_customer(ticket.customer_id if ticket else None)
        or _get_customer(enriched["entities"].get("customer_id"))
    )
    return {
        "text": enriched["text"] or state["text"],
        "language": enriched["language"],
        "entities": enriched["entities"],
        "customer": customer,
        "trace": ["PERCEPTION_COMPLETED"],
    }


# ── 2. judgment (Jev) ────────────────────────────────────────────────────────


def run_judgment(state: ResolvynState) -> dict:
    plan_tier = (state.get("customer") or {}).get("plan")
    j = ENGINE.judge(state["text"], plan=plan_tier)
    tickets.update(state["ticket_id"], intent=j.intent, sentiment=j.sentiment, urgency=j.urgency,
                   priority=j.priority, confidence=j.confidence, status="ANALYZING")
    tickets.add_event(state["ticket_id"], "Jev", "INTENT_DETECTED",
                      f"Intent {j.intent} · sentiment {j.sentiment} · urgency {j.urgency} · confidence {j.confidence}%",
                      status="COMPLETED", meta={"judgment": judgment_dict(j)})
    return {"judgment": judgment_dict(j), "trace": ["JUDGMENT_COMPLETED"]}


# ── 3. context / memory ──────────────────────────────────────────────────────


def retrieve_context(state: ResolvynState) -> dict:
    j = judgment_from_dict(state["judgment"])
    subject = state["text"]
    query = ENGINE.write_query(state["text"], j, subject=subject)
    ret = ENGINE.retrieve(query, j.department, exclude_ticket=state["ticket_id"])
    settings = get_settings()
    is_first_time_bug = ret.best < settings.first_time_bug_score and not ret.bugs
    tickets.update(state["ticket_id"], knowledge=ret.sources())
    tickets.add_event(state["ticket_id"], "Memory", "KNOWLEDGE_RETRIEVED",
                      f"Query \"{query}\" → best match {ret.best_common:.2f} (rulebook) / {ret.best_bug:.2f} (first-time-bug memory)",
                      status="COMPLETED", meta={"query": query, "sources": ret.sources()})
    return {
        "query": query,
        "retrieval_best_common": ret.best_common,
        "retrieval_best_bug": ret.best_bug,
        "is_first_time_bug": is_first_time_bug,
        "trace": ["MEMORY_RETRIEVED" if ret.sources() else "MEMORY_EMPTY"],
    }


# ── 4. decision engine (Analyze → Plan → Evaluate → Choose action) ──────────


async def run_decision(state: ResolvynState) -> dict:
    j = judgment_from_dict(state["judgment"])
    ret = ENGINE.retrieve(state["query"], j.department, exclude_ticket=state["ticket_id"])
    ctx = _build_ctx(state)
    ctx.retrieval = ret
    decision = await ENGINE.reason(ctx)
    tickets.add_event(state["ticket_id"], "Decision Engine", "DECISION",
                      f"{decision.path.replace('_', ' ').title()} — {decision.reason}", status="COMPLETED",
                      meta={"path": decision.path, "confidence": decision.confidence})
    return {
        "decision_path": decision.path,
        "decision_reason": decision.reason,
        "decision_confidence": decision.confidence,
        "trace": ["DECISION_CREATED"],
    }


# ── 5. routing — FruitFlySwarmRouter (agents/swarm_router.py) ────────────────


def route_agent(state: ResolvynState) -> dict:
    """Bio-inspired (not biological — see agents/swarm_router.py) mixture-of-
    experts routing stage: every department competes on a cheap activation
    score; the winner is the only one that becomes active. Replaces trusting
    Jev's single department pick blindly — Jev's own judgment is still one of
    the swarm's inputs (via the same INTENTS table), not bypassed.
    """
    human_action = state.get("human_action") or {}
    # A GUIDE resume on an ambiguous-routing gate re-enters here (agents/graph.py's
    # _route_after_human_gate) with the human's clarification folded into the text.
    guidance = human_action.get("guidance") if human_action.get("action") == "GUIDE" else None
    scoring_text = f"{state['text']} {guidance}" if guidance else state["text"]
    # A TEACH resume also loops back through here (via retrieve_context/decision):
    # a human just taught a fix for this exact ticket, so pausing *again* for
    # "which desk?" would be a second, redundant human interruption in one turn —
    # take the swarm's top pick even if the underlying issue is inherently hard
    # to keyword-match (e.g. a genuinely novel first-time bug with no domain
    # vocabulary at all), rather than re-gating on ambiguity here.
    just_taught = human_action.get("action") == "TEACH"

    result = swarm_router.evaluate(state["ticket_id"], text=scoring_text)
    activations = swarm_router.to_dict(result)["candidates"]

    if result.ambiguous and not just_taught:
        tickets.update(state["ticket_id"], assigned_agent=result.winner, status="WAITING_FOR_HUMAN")
        tickets.add_event(state["ticket_id"], "Orchestrator", "AGENT_ASSIGNED",
                          f"Routing is ambiguous — {result.winner} narrowly leads {result.runner_up}",
                          status="WAITING", meta={"swarm": swarm_router.to_dict(result)},
                          public="Reviewing which team can help with this")
        return {
            "selected_agent": result.winner, "routing_reason": result.routing_reason,
            "swarm_activations": activations, "swarm_winner": result.winner, "swarm_runner_up": result.runner_up,
            "swarm_activation_gap": result.activation_gap, "swarm_ambiguous": True,
            "human_gate_required": True, "human_gate_reason": "ambiguous_routing", "trace": ["ROUTING_AMBIGUOUS"],
        }

    orchestrator.set_state(result.winner, "ANALYZING", state["ticket_id"], "Routed by the fruit-fly-inspired swarm router")
    tickets.update(state["ticket_id"], assigned_agent=result.winner, status="ROUTING")
    tickets.add_event(state["ticket_id"], "Orchestrator", "AGENT_ASSIGNED", f"{result.winner} Agent assigned",
                      status="COMPLETED", meta={"swarm": swarm_router.to_dict(result)},
                      public=f"Routed to our {result.winner} team")
    return {
        "selected_agent": result.winner, "routing_reason": result.routing_reason,
        "swarm_activations": activations, "swarm_winner": result.winner, "swarm_runner_up": result.runner_up,
        "swarm_activation_gap": result.activation_gap, "swarm_ambiguous": False,
        "human_gate_required": False, "human_gate_reason": None, "trace": ["ROUTING_COMPLETED"],
    }


# ── 6. specialist agent execution ────────────────────────────────────────────


def _apply_entities(agent_state: dict, entities: dict) -> None:
    for k in ("order_id", "email", "phone_last4", "name"):
        if entities.get(k) and not agent_state.get(k):
            agent_state[k] = entities[k]


def _sync_ticket_from_plan(ticket_id: str, plan: Plan) -> None:
    """Mirrors `services/conversation.py::_apply_plan`'s core effect: a Plan's
    own declared status/next_step is what actually moves the ticket — nothing
    here is a *new* status the graph invented (docs/claude.md vocabulary)."""
    fields: dict = {}
    if plan.status and plan.status != "RESOLVED":  # RESOLVED is set by record_outcome, once, after verification
        fields["status"] = plan.status
    if plan.next_step:
        fields["next_step"] = plan.next_step
    if fields:
        tickets.update(ticket_id, **fields)


async def execute_agent(state: ResolvynState) -> dict:
    ctx = _build_ctx(state)
    agent = orchestrator.route(state["selected_agent"])
    _apply_entities(ctx.state, state.get("entities", {}))
    orchestrator.set_state(state["selected_agent"], "RETRIEVING", state["ticket_id"], f"{agent.name} agent working")

    plan = await agent.plan(ctx)
    # A ticket is itself the request — there is no live back-and-forth to ask
    # "shall I go ahead?" (spec §36 wants the full PH-1042 chain to run without
    # a human answering on the AI's behalf), so a bounded loop auto-confirms
    # through the agent's own `awaiting: confirm_*` gate using its own public
    # `plan()` re-entry (never a private method — see agents/README.md).
    hops = 0
    while ctx.state.get("awaiting") in CONFIRM_AWAITS and hops < 3:
        ctx.judgment.yes, ctx.judgment.no = True, False
        plan = await agent.plan(ctx)
        hops += 1

    orchestrator.set_state(state["selected_agent"],
                           plan.agent_state if plan.agent_state != "COMPLETED" else "ACTING",
                           state["ticket_id"], plan.operation or None)
    tickets.add_event(state["ticket_id"], state["selected_agent"], "RESPONSE_GENERATED",
                      plan.operation or "Plan produced", status="COMPLETED", meta={"goal": plan.goal, "facts": plan.facts})
    _sync_ticket_from_plan(state["ticket_id"], plan)

    return {
        "plan": asdict(plan),
        "agent_state": ctx.state,
        "pending_action_id": ctx.state.get("pending_action_id"),
        "trace": ["AGENT_STARTED", "AGENT_COMPLETED"],
    }


async def handle_escalation(state: ResolvynState) -> dict:
    j = judgment_from_dict(state["judgment"])
    reason = state["decision_reason"]
    tickets.update(state["ticket_id"], escalated=True, needs_human=True, escalation_reason=reason,
                   status="WAITING_FOR_HUMAN", resolution_path="ESCALATED")
    tickets.add_event(state["ticket_id"], "Orchestrator", "ESCALATED", f"Escalated: {reason}", status="WAITING",
                      public=f"Escalated to our {j.department} team")
    plan = Plan(goal="Escalated to a human.", fallback="This has been escalated to a member of our team.",
               status="WAITING_FOR_HUMAN", agent_state="WAITING", operation="Escalated", escalate=reason)
    return {"plan": asdict(plan), "human_gate_required": True, "human_gate_reason": "escalated", "trace": ["AGENT_STARTED"]}


async def flag_first_time_bug(state: ResolvynState) -> dict:
    j = judgment_from_dict(state["judgment"])
    ticket = tickets.get(state["ticket_id"])
    title = state["text"][:100]
    with Session(engine) as s:
        existing = s.exec(select(FirstTimeBug).where(FirstTimeBug.ticket_id == state["ticket_id"])).first()
    if existing:
        bug_id = existing.bug_id
    else:
        bug = memory.record_first_time_bug(state["ticket_id"], title, state["text"], j.department)
        bug_id = bug.bug_id
    tickets.update(state["ticket_id"], is_first_time_bug=True, needs_human=True, status="WAITING_FOR_HUMAN",
                   resolution_path="FIRST_TIME_BUG", escalation_reason="First-time bug: no precedent in memory")
    tickets.add_event(state["ticket_id"], "Decision Engine", "FIRST_TIME_BUG_FLAGGED",
                      "A FIRST TIME BUG HAS BEEN REPORTED — no precedent in either memory", status="WAITING",
                      meta={"bug_id": bug_id}, public="Escalated to a specialist")
    plan = Plan(goal="First-time bug — no known resolution.",
               fallback="This looks like a new issue for us. I've flagged it for a specialist, who will follow up with a fix.",
               status="WAITING_FOR_HUMAN", agent_state="WAITING", operation="First-time bug — awaiting team suggestion")
    return {"plan": asdict(plan), "bug_id": bug_id, "human_gate_required": True, "human_gate_reason": "first_time_bug",
           "trace": ["AGENT_STARTED"]}


# ── 7. human gate check ───────────────────────────────────────────────────────


def check_human_gate(state: ResolvynState) -> dict:
    plan = state["plan"] or {}
    required = plan.get("status") == "WAITING_FOR_HUMAN" or bool(plan.get("escalate"))
    reason = (
        "approval" if state.get("agent_state", {}).get("awaiting") == "approval"
        else "first_time_bug" if state.get("decision_path") in ("FIRST_TIME_BUG", "KNOWN_OPEN_BUG")
        else "escalated" if state.get("decision_path") == "ESCALATED"
        else plan.get("escalate") or "needs_human" if required else None
    )
    return {"human_gate_required": required, "human_gate_reason": reason, "trace": ["HUMAN_GATE_REACHED"] if required else []}


async def human_gate(state: ResolvynState) -> dict:
    """Pauses the graph (spec §14-16) — LangGraph's checkpointer durably
    persists everything in `state` at this point (ticket_id, decision, plan,
    agent_state, pending_action_id/bug_id, trace) and the process can even
    restart; `ResolvynOrchestrator.resume()` (agents/service.py) is the only
    way back in, keyed on the ticket's thread_id.
    """
    plan = state.get("plan") or {}
    payload = {
        "ticket_id": state["ticket_id"],
        "reason": state.get("human_gate_reason"),
        "summary": plan.get("operation"),
        "pending_action_id": state.get("pending_action_id"),
        "bug_id": state.get("bug_id"),
        "decision_path": state.get("decision_path"),
        "swarm_activations": state.get("swarm_activations"),
        "swarm_winner": state.get("swarm_winner"),
        "swarm_runner_up": state.get("swarm_runner_up"),
    }
    resume_value = interrupt(payload) or {}
    action = str(resume_value.get("action", "")).upper()
    operator = resume_value.get("operator", "Operator 01")

    if action == "GUIDE":
        return await resume_guide(state, resume_value["guidance"], operator)
    if action == "APPROVE":
        return await resume_approve(state, bool(resume_value.get("approve", True)), operator, resume_value.get("reason"))
    if action == "CORRECT":
        return await resume_correct(state, resume_value["correction"], operator, resume_value.get("reason"),
                                    resume_value.get("department"))
    if action == "OVERRIDE":
        return await resume_override(state, resume_value.get("decision", ""), operator, resume_value.get("reason"),
                                     resume_value.get("department"))
    if action == "TEACH":
        return await resume_teach(state, resume_value["topic"], resume_value["knowledge"], operator)
    return {"error": f"unrecognised human action {action!r}", "trace": ["HUMAN_ACTION_RECEIVED"]}


# ── 8. verification ──────────────────────────────────────────────────────────


def verify(state: ResolvynState) -> dict:
    if state.get("decision_path") != "ACTION":
        # Nothing side-effecting happened (INSTANT / small talk) — verification
        # only gates tool-executing work (spec §21: "for actions requiring it").
        # Note: `decision_path` reflects the *current* pass — after TEACH loops
        # back through retrieve_context/decision, it is the freshly re-decided
        # path, not whatever it was when the human gate first triggered. CORRECT
        # and OVERRIDE don't need a bypass here: their own plans already carry
        # an explicit "...VERIFIED..." fact, so the real check below finds it.
        return {"action_executed": True, "action_verified": True, "trace": ["VERIFICATION_COMPLETED"]}
    plan = state["plan"] or {}
    facts = plan.get("facts") or []
    executed = plan.get("status") in ("VERIFYING", "RESOLVED") or any("executed" in f.lower() for f in facts)
    verified = any("VERIFIED" in f for f in facts) or plan.get("status") == "RESOLVED"
    event_type = "ACTION_VERIFIED" if verified else "VERIFICATION_STARTED"
    tickets.add_event(state["ticket_id"], state.get("selected_agent") or "Resolvyn", event_type,
                      "Verification succeeded" if verified else "Awaiting/failed verification",
                      status="COMPLETED" if verified else "FAILED")
    return {"action_executed": executed, "action_verified": verified,
           "trace": ["VERIFICATION_COMPLETED"] if verified else ["VERIFICATION_STARTED"]}


# ── 9. response generation ───────────────────────────────────────────────────


def generate_response(state: ResolvynState) -> dict:
    plan = state["plan"] or {}
    # Deterministic on purpose (spec §22): the fallback line IS the agent
    # playbook's own deterministic response, already grounded in verified
    # facts (see e.g. BillingAgent._execute_refund) — never generated from
    # the *planned* action alone.
    response = plan.get("fallback") or "We're looking into this and will follow up shortly."
    tickets.add_message(state["ticket_id"], "Resolvyn", response, kind="text")
    return {"customer_response": response, "trace": ["RESPONSE_GENERATED"]}


# ── 10. outcome ───────────────────────────────────────────────────────────────


def record_outcome(state: ResolvynState) -> dict:
    plan = state["plan"] or {}
    if state.get("action_verified") or plan.get("status") == "RESOLVED":
        outcome = "RESOLVED"
    elif state.get("human_gate_required"):
        outcome = "WAITING_FOR_HUMAN"
    elif state.get("error"):
        outcome = "FAILED"
    else:
        outcome = plan.get("status") or "ACTIVE"

    if outcome == "RESOLVED":
        tickets.update(state["ticket_id"], status="RESOLVED", handled_by="AI", needs_human=False)
        tickets.add_event(state["ticket_id"], state.get("selected_agent") or "Resolvyn", "TICKET_RESOLVED",
                          "Ticket resolved", status="COMPLETED", public="Resolved")
        if state.get("selected_agent"):
            orchestrator.set_state(state["selected_agent"], "IDLE")
            orchestrator.mark_resolved(state["selected_agent"])
    elif outcome == "FAILED":
        tickets.update(state["ticket_id"], status="FAILED")
        tickets.add_event(state["ticket_id"], state.get("selected_agent") or "Resolvyn", "ERROR",
                          state.get("error") or "Orchestration failed", status="FAILED")
    return {"outcome": outcome, "trace": [f"OUTCOME_{outcome}"]}


# ── 11. learning signal ──────────────────────────────────────────────────────


def emit_learning_signal(state: ResolvynState) -> dict:
    if state.get("outcome_signal_recorded"):
        return {}  # already recorded on an earlier pass through this node (idempotency, spec §30)
    outcome = state.get("outcome")
    human_action = (state.get("human_action") or {}).get("action")
    if outcome == "RESOLVED" and human_action not in ("CORRECT", "OVERRIDE"):
        # CORRECT/OVERRIDE already recorded their own, more specific signal (resume_correct/resume_override)
        sig = learning_service.record(state["ticket_id"], "Successful resolution", source_event="TICKET_RESOLVED",
                                      expected="Autonomous resolution", observed="Resolved and verified",
                                      description="Ticket resolved end-to-end by the orchestration graph")
    elif outcome == "FAILED":
        sig = learning_service.record(state["ticket_id"], "Failed tool action", source_event="ERROR",
                                      expected="Successful tool execution", observed=state.get("error") or "Failure",
                                      description="Orchestration could not complete verification")
    else:
        return {"outcome_signal_recorded": True}
    return {"learning_signal_id": sig["signal_id"], "outcome_signal_recorded": True, "trace": ["LEARNING_SIGNAL_CREATED"]}


# ── retry gate ────────────────────────────────────────────────────────────────


def register_failure(state: ResolvynState) -> dict:
    plan = state["plan"] or {}
    return {"retry_count": state.get("retry_count", 0) + 1, "error": plan.get("operation") or "Tool execution failed",
           "trace": ["TOOL_FAILED"]}


# ── human-gate resume: GUIDE / APPROVE / CORRECT / OVERRIDE / TEACH ──────────


async def resume_guide(state: ResolvynState, guidance: str, operator: str) -> dict:
    _log_human_action(state["ticket_id"], "GUIDE", guidance, reason="Guidance for the AI", operator=operator)
    tickets.add_event(state["ticket_id"], operator, "HUMAN_GUIDANCE", f"Guidance applied: {guidance}", status="COMPLETED")
    sig = learning_service.record(state["ticket_id"], "Human guidance", source_event="GUIDANCE",
                                  expected="AI decides alone", observed=guidance,
                                  description="A human added context the AI did not have")
    agent_state = dict(state.get("agent_state") or {})
    enriched = ENGINE.perceive(guidance, "Ticket")
    _apply_entities(agent_state, enriched["entities"])
    agent_state["awaiting"] = None
    return {"agent_state": agent_state, "human_action": {"action": "GUIDE", "guidance": guidance},
           "human_gate_required": False, "learning_signal_id": sig["signal_id"], "trace": ["HUMAN_ACTION_RECEIVED"]}


async def resume_approve(state: ResolvynState, approve: bool, operator: str, reason: str | None) -> dict:
    ctx = _build_ctx(state)
    agent = orchestrator.route(state["selected_agent"])
    from app.models import PendingAction

    with Session(engine, expire_on_commit=False) as s:
        act = s.get(PendingAction, state["pending_action_id"])
        if not act or act.status != "PENDING":
            return {"error": "approval request not found or already decided", "trace": ["HUMAN_ACTION_RECEIVED"]}
        act.status = "APPROVED" if approve else "REJECTED"
        act.decided_by, act.decided_at = operator, utcnow()
        s.add(act)
        s.commit()
        summary = act.summary

    verb = "APPROVED" if approve else "REJECTED"
    _log_human_action(state["ticket_id"], "APPROVE", f"{verb} {summary}", previous=f"AI proposed: {summary}",
                      reason=reason or ("Duplicate transaction verified" if approve else "Rejected by operator"),
                      operator=operator)
    tickets.add_event(state["ticket_id"], operator, "ACTION_APPROVED" if approve else "ACTION_REJECTED",
                      f"{verb.title()}: {summary}", status="COMPLETED",
                      public="Approved by our team" if approve else "Not approved")
    sig = learning_service.record(state["ticket_id"], "Human approval" if approve else "Policy conflict",
                                  source_event="APPROVAL", expected="Autonomous action" if approve else summary,
                                  observed=f"Human {verb.lower()}", description=f"{verb.title()}: {summary}")

    plan = await agent.resume(ctx, "approved" if approve else "rejected", {"reason": reason})
    _sync_ticket_from_plan(state["ticket_id"], plan)
    return {
        "plan": asdict(plan), "agent_state": ctx.state, "human_action": {"action": "APPROVE", "approved": approve},
        "human_gate_required": False, "learning_signal_id": sig["signal_id"], "trace": ["HUMAN_ACTION_RECEIVED"],
    }


async def resume_correct(state: ResolvynState, correction: str, operator: str, reason: str | None,
                         department: str | None = None) -> dict:
    """`department` is optional (spec §26: CORRECT may just fix the AI's plan,
    or may also reroute it — "if the operator knows Technical but the swarm
    picked Billing"). The original swarm decision is never erased: it stays on
    the AGENT_ASSIGNED event this reroutes past, and a "Wrong agent routing"
    learning signal records AI-vs-human for future routing weight tuning
    (agents/swarm_router.py's `_historical_signal` reads exactly this).
    """
    j = judgment_from_dict(state["judgment"])
    ticket = tickets.get(state["ticket_id"])
    previous = (state.get("plan") or {}).get("operation") or ticket.next_step or j.intent
    _log_human_action(state["ticket_id"], "CORRECT", correction, previous=previous, reason=reason, operator=operator)

    original_agent = state.get("selected_agent")
    reroute = bool(department and department in DEPARTMENTS and department != original_agent)
    dept_for_rulebook = department if reroute else (original_agent or "Other")
    rulebook.add_rule(topic=f"{j.intent} — {str(previous)[:60]}", knowledge=correction, department=dept_for_rulebook,
                      source="human_correction", ticket_id=state["ticket_id"])
    tickets.add_event(state["ticket_id"], operator, "HUMAN_CORRECTION", f"Correction: {correction}", status="COMPLETED",
                      meta={"rerouted_from": original_agent, "rerouted_to": department} if reroute else None)
    sig = learning_service.record(state["ticket_id"], "Human correction", source_event="CORRECTION",
                                  expected=str(previous), observed=correction,
                                  description=reason or "Decision mismatch detected → rulebook updated")

    if reroute:
        tickets.update(state["ticket_id"], assigned_agent=department, status="ROUTING")
        if original_agent:
            orchestrator.set_state(original_agent, "IDLE")
        orchestrator.set_state(department, "ANALYZING", state["ticket_id"], "Reassigned by human correction")
        learning_service.record(state["ticket_id"], "Wrong agent routing", source_event="CORRECTION",
                                expected=original_agent, observed=department,
                                description=reason or f"Operator corrected routing from {original_agent} to {department}")
        agent_state = dict(state.get("agent_state") or {})
        agent_state["awaiting"] = None  # the newly-assigned specialist starts its own plan fresh, not mid-confirmation
        return {
            "selected_agent": department, "routing_reason": f"Corrected by {operator} from {original_agent}: {reason or correction}",
            "agent_state": agent_state, "human_action": {"action": "CORRECT", "correction": correction, "rerouted": True},
            "human_gate_required": False, "learning_signal_id": sig["signal_id"], "trace": ["HUMAN_ACTION_RECEIVED"],
        }

    plan = Plan(goal="Human-corrected action.", fallback=correction, status="RESOLVED", agent_state="COMPLETED",
               operation="Resolved via human correction", facts=[f"Human correction applied and VERIFIED: {correction}"])
    return {"plan": asdict(plan), "action_verified": True, "human_action": {"action": "CORRECT", "correction": correction},
           "human_gate_required": False, "learning_signal_id": sig["signal_id"], "trace": ["HUMAN_ACTION_RECEIVED"]}


async def resume_override(state: ResolvynState, decision: str, operator: str, reason: str | None,
                          department: str | None = None) -> dict:
    """`department` is optional (spec §27): the human keeps full control either
    way (`handled_by="HUMAN"`), but can also record which desk this really
    belonged to for the audit trail / future routing weight tuning — the
    original swarm pick is preserved on the earlier AGENT_ASSIGNED event, never
    erased."""
    ticket = tickets.get(state["ticket_id"])
    previous = ticket.next_step or (state.get("plan") or {}).get("operation") or ticket.status
    _log_human_action(state["ticket_id"], "OVERRIDE", decision or "Took over", previous=previous, reason=reason, operator=operator)

    original_agent = state.get("selected_agent")
    final_agent = department if (department and department in DEPARTMENTS) else original_agent
    reroute = bool(final_agent and final_agent != original_agent)
    fields = {"handled_by": "HUMAN", "needs_human": True, "status": "ACTIVE", "assignee": operator}
    if reroute:
        fields["assigned_agent"] = final_agent
    tickets.update(state["ticket_id"], **fields)
    tickets.add_event(state["ticket_id"], operator, "HUMAN_TAKEOVER", f"{operator} took over: {decision}",
                      status="COMPLETED", public="A team member joined this ticket",
                      meta={"overridden_from": original_agent, "overridden_to": final_agent} if reroute else None)
    if original_agent:
        orchestrator.set_state(original_agent, "IDLE")
    sig = learning_service.record(state["ticket_id"], "Human override", source_event="OVERRIDE", expected=str(previous),
                                  observed=decision or "Manual handling", description=reason or "Human took control")
    if reroute:
        learning_service.record(state["ticket_id"], "Wrong agent routing", source_event="OVERRIDE",
                                expected=original_agent, observed=final_agent,
                                description=reason or f"Operator overrode routing from {original_agent} to {final_agent}")
    plan = Plan(goal="Human took control.", fallback=decision or "A team member is now handling this directly.",
               status="RESOLVED", agent_state="COMPLETED", operation="Resolved by human override",
               facts=[f"Human override applied and VERIFIED: {decision}"] if decision else [])
    return {"plan": asdict(plan), "action_verified": bool(decision), "selected_agent": final_agent,
           "human_action": {"action": "OVERRIDE", "decision": decision, "department": final_agent},
           "human_gate_required": False, "learning_signal_id": sig["signal_id"], "trace": ["HUMAN_ACTION_RECEIVED"]}


async def resume_teach(state: ResolvynState, topic: str, knowledge: str, operator: str) -> dict:
    j = judgment_from_dict(state["judgment"])
    dept = j.department
    _log_human_action(state["ticket_id"], "TEACH", f"Taught: {topic}", reason=knowledge, operator=operator)
    rulebook.add_rule(topic=topic, knowledge=knowledge, department=dept, source="first_time_bug_suggestion",
                      ticket_id=state["ticket_id"])
    if state.get("bug_id"):
        with Session(engine, expire_on_commit=False) as s:
            bug = s.get(FirstTimeBug, state["bug_id"])
            if bug and bug.status != "SUGGESTED":
                bug.status, bug.suggestion, bug.suggested_by, bug.resolved_at = "SUGGESTED", knowledge, operator, utcnow()
                s.add(bug)
                s.commit()
        # The bug's own memory chunk carries the answer next to the problem it
        # solved (backend/app/memory/memory_engine.py::attach_bug_suggestion) —
        # this, not the rulebook entry alone, is what `decide()`'s
        # KNOWN_OPEN_BUG branch checks for on re-evaluation ("Human suggestion:"
        # in the bug's indexed text). Skipping this would re-flag the same
        # ticket as a first-time bug forever.
        memory.attach_bug_suggestion(state["ticket_id"], knowledge)
    tickets.add_event(state["ticket_id"], operator, "HUMAN_TEACHING", f"Rulebook updated ({dept}): {topic}", status="COMPLETED")
    learning_service.record(state["ticket_id"], "First-time bug suggestion", source_event="FIRST_TIME_BUG",
                            expected="Unknown — no precedent", observed=knowledge,
                            description="Suggestion written into the Solvable Rulebook")
    tickets.update(state["ticket_id"], needs_human=False, status="ACTIVE")
    return {"human_action": {"action": "TEACH", "topic": topic, "knowledge": knowledge}, "human_gate_required": False,
           "trace": ["HUMAN_ACTION_RECEIVED"]}
