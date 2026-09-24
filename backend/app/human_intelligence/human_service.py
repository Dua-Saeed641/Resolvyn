"""Human Intelligence Layer — GUIDE, APPROVE, CORRECT, OVERRIDE, TEACH.

Humans are embedded in the loop, not just an escalation destination
(docs/context.md). Every action here (docs/claude.md, "State consistency"):
  1. writes a HumanAction row (the audit log, project.md §85),
  2. updates ticket / agent / live-session state,
  3. shows up in the activity timeline, and
  4. can emit a learning signal — and, where it carries knowledge, extends the
     Solvable Rulebook so the AI behaves differently next time.
"""

from sqlmodel import Session

from app.agents import orchestrator
from app.database import engine
from app.learning import learning_service
from app.memory import rulebook
from app.memory.memory_engine import memory
from app.models import FirstTimeBug, HumanAction, PendingAction
from app.services import conversation
from app.services import ticket_service as tickets
from app.services.realtime import hub
from app.services.sessions import sessions
from app.utils import jload, utcnow
from app.vocab import DEPARTMENTS, HUMAN_EVENT_FOR_ACTION

OPERATOR = "Operator 01"


class HumanActionError(ValueError):
    pass


def _log(ticket_id: str | None, action: str, human_action: str, *, previous: str | None = None,
         reason: str | None = None, operator: str = OPERATOR) -> dict:
    with Session(engine, expire_on_commit=False) as s:
        row = HumanAction(ticket_id=ticket_id, event_type=HUMAN_EVENT_FOR_ACTION[action], previous_ai_action=previous,
                          human_action=human_action, reason=reason, operator=operator)
        s.add(row)
        s.commit()
    d = tickets.human_dict(row)
    hub.to_ops({"type": "human_action", "action": d})
    return d


def _require_ticket(ticket_id: str):
    t = tickets.get(ticket_id)
    if not t:
        raise HumanActionError(f"ticket {ticket_id} not found")
    return t


def _guidance(ticket_id: str, text: str) -> None:
    t = tickets.get(ticket_id)
    items = (t.guidance_json and jload(t.guidance_json, [])) or []
    items.append(text)
    tickets.update(ticket_id, guidance=items)
    s = sessions.by_ticket(ticket_id)
    if s:
        s.guidance.append(text)


# ── GUIDE ────────────────────────────────────────────────────────────────────


def guide(ticket_id: str, text: str, operator: str = OPERATOR) -> dict:
    """Tell the AI what to consider. Injected into the live call's next turns."""
    _require_ticket(ticket_id)
    if not text.strip():
        raise HumanActionError("guidance is empty")
    _guidance(ticket_id, text.strip())
    row = _log(ticket_id, "GUIDE", text.strip(), reason="Guidance for the AI", operator=operator)
    tickets.add_event(ticket_id, operator, "HUMAN_GUIDANCE", f"Guidance applied: {text.strip()}", status="COMPLETED")
    learning_service.record(ticket_id, "Human guidance", source_event="GUIDANCE", expected="AI decides alone",
                            observed=text.strip(), description="A human added context the AI did not have")
    return row


# ── APPROVE / REJECT ─────────────────────────────────────────────────────────


async def decide_action(ticket_id: str, action_id: int, approve: bool, operator: str = OPERATOR, reason: str | None = None) -> dict:
    """The human approval gate (docs/architecture.md §2.5)."""
    _require_ticket(ticket_id)
    with Session(engine, expire_on_commit=False) as s:
        act = s.get(PendingAction, action_id)
        if not act or act.ticket_id != ticket_id:
            raise HumanActionError("approval request not found for this ticket")
        if act.status != "PENDING":
            raise HumanActionError(f"already {act.status.lower()}")
        act.status = "APPROVED" if approve else "REJECTED"
        act.decided_by, act.decided_at = operator, utcnow()
        s.add(act)
        s.commit()
    params = jload(act.params_json, {})
    verb = "APPROVED" if approve else "REJECTED"
    row = _log(ticket_id, "APPROVE", f"{verb} {act.action_type.upper()}: {act.summary}", previous=f"AI proposed: {act.summary}",
               reason=reason or ("Duplicate transaction verified" if approve else "Rejected by operator"), operator=operator)
    tickets.add_event(ticket_id, operator, "ACTION_APPROVED" if approve else "ACTION_REJECTED",
                      f"{verb.title()}: {act.summary}", status="COMPLETED",
                      public="Refund approved by our team" if approve else "Refund not approved")
    learning_service.record(
        ticket_id, "Human approval" if approve else "Policy conflict", source_event="APPROVAL",
        expected="Autonomous refund" if approve else act.summary, observed=f"Human {verb.lower()}",
        description=("Human approved the AI's proposed action" if approve else "Human rejected the AI's proposed action") + f": {act.summary}",
    )
    hub.to_ops({"type": "approval_decided", "action": tickets.pending_dict(act), "ticket_id": ticket_id})
    session = sessions.by_ticket(ticket_id)
    if session is not None:
        session.state["awaiting"] = None
    await _resume_safely(ticket_id, "approved" if approve else "rejected", {"params": params, "reason": reason})
    return row


async def _resume_safely(ticket_id: str, event: str, payload: dict) -> None:
    """The human's decision is already recorded; a failure while the AI carries on must be visible, not silent."""
    try:
        await conversation.resume(ticket_id, event, payload)
    except Exception as e:  # noqa: BLE001
        print(f"[human_service] resume after {event} failed: {type(e).__name__}: {e}", flush=True)
        tickets.add_event(ticket_id, "Resolvyn", "ERROR", f"AI could not continue after human {event}: {type(e).__name__}",
                          status="FAILED")
        tickets.update(ticket_id, status="WAITING_FOR_HUMAN", needs_human=True,
                       next_step=f"AI could not finish after the {event} — a team member should complete this")


# ── CORRECT ──────────────────────────────────────────────────────────────────


def correct(ticket_id: str, correct_action: str, ai_decision: str | None = None, reason: str | None = None,
            operator: str = OPERATOR) -> dict:
    """Fix an AI decision. Becomes guidance now AND a rule for next time."""
    t = _require_ticket(ticket_id)
    if not correct_action.strip():
        raise HumanActionError("the corrected action is empty")
    previous = ai_decision or t.next_step or t.one_line_summary or "AI decision"
    row = _log(ticket_id, "CORRECT", correct_action.strip(), previous=previous, reason=reason, operator=operator)
    _guidance(ticket_id, f"Correction: {correct_action.strip()}")
    dept = t.assigned_agent if t.assigned_agent in DEPARTMENTS else "Other"
    rule = rulebook.add_rule(topic=f"{t.intent or 'Correction'} — {previous[:60]}", knowledge=correct_action.strip(),
                             department=dept, source="human_correction", ticket_id=ticket_id)
    tickets.add_event(ticket_id, operator, "HUMAN_CORRECTION", f"Correction: {correct_action.strip()}", status="COMPLETED",
                      meta={"rule_id": rule.rule_id})
    learning_service.record(ticket_id, "Human correction", source_event="CORRECTION", expected=previous,
                            observed=correct_action.strip(), description=reason or "Decision mismatch detected → rulebook updated")
    return row


# ── OVERRIDE / take over ─────────────────────────────────────────────────────


def override(ticket_id: str, new_decision: str, reason: str | None = None, operator: str = OPERATOR) -> dict:
    """Take control of the ticket: the AI stops replying, the human owns it."""
    t = _require_ticket(ticket_id)
    previous = t.next_step or t.one_line_summary or "AI action"
    row = _log(ticket_id, "OVERRIDE", new_decision.strip() or "Took over the conversation", previous=previous, reason=reason, operator=operator)
    session = sessions.by_ticket(ticket_id)
    if session:
        session.human_active = True
        session.cancel_turn()
    tickets.update(ticket_id, handled_by="HUMAN", needs_human=True, status="ACTIVE", assignee=operator)
    tickets.add_event(ticket_id, operator, "HUMAN_TAKEOVER", f"{operator} took over: {new_decision.strip() or 'manual handling'}",
                      status="COMPLETED", public="A team member joined your conversation")
    if t.assigned_agent:
        orchestrator.set_state(t.assigned_agent, "IDLE")
    learning_service.record(ticket_id, "Human override", source_event="OVERRIDE", expected=previous,
                            observed=new_decision.strip() or "Manual handling", description=reason or "Human took control")
    return row


def say(ticket_id: str, text: str, operator: str = OPERATOR) -> dict:
    """A team member speaks/types to the caller (spoken through the same voice channel)."""
    t = _require_ticket(ticket_id)
    if not t.session_id:
        raise HumanActionError("this ticket has no live session")
    s = sessions.by_ticket(ticket_id)
    if s is None:
        raise HumanActionError("the caller is no longer connected")
    if not text.strip():
        raise HumanActionError("message is empty")
    s.seq += 1
    hub.to_session(s.session_id, {"type": "agent_sentence", "turn": s.seq, "text": text.strip(), "say": text.strip(),
                                  "lang": s.language, "filler": False, "sender": "human"})
    hub.to_session(s.session_id, {"type": "agent_done", "turn": s.seq})
    return tickets.add_message(ticket_id, "HUMAN", text.strip(), kind="speech")


async def resolve_by_human(ticket_id: str, note: str | None = None, operator: str = OPERATOR) -> dict:
    t = _require_ticket(ticket_id)
    row = _log(ticket_id, "OVERRIDE", "Marked resolved", previous=t.status, reason=note or "Resolved by team member", operator=operator)
    s = sessions.by_ticket(ticket_id)
    if s is None:
        s = sessions.create(channel=t.channel, session_id=t.session_id)
        s.ticket_id = ticket_id
        s.closed = True
    await conversation.finalize_resolution(s, by="HUMAN")
    return row


# ── TEACH ────────────────────────────────────────────────────────────────────


def teach(topic: str, knowledge: str, department: str = "Other", ticket_id: str | None = None,
          operator: str = OPERATOR) -> dict:
    """Add operational knowledge to the Solvable Rulebook (project.md §27)."""
    if not topic.strip() or not knowledge.strip():
        raise HumanActionError("topic and knowledge are both required")
    rule = rulebook.add_rule(topic, knowledge, department, "human_teach", ticket_id)
    row = _log(ticket_id, "TEACH", f"Taught: {topic.strip()}", reason=knowledge.strip(), operator=operator)
    if ticket_id:
        tickets.add_event(ticket_id, operator, "HUMAN_TEACHING", f"Rulebook updated ({department}): {topic.strip()}", status="COMPLETED")
        learning_service.record(ticket_id, "Human teaching", source_event="TEACHING", expected="No rule for this case",
                                observed=knowledge.strip(), description=f"New rule added to the {department} rulebook: {topic.strip()}")
    hub.to_ops({"type": "rulebook_updated", "rule_id": rule.rule_id})
    return row


# ── first-time bug: manager's suggestion ─────────────────────────────────────


async def suggest_for_bug(bug_id: int, suggestion: str, operator: str = OPERATOR) -> dict:
    """The manager answers "A FIRST TIME BUG HAS BEEN REPORTED — PLEASE ENTER YOUR SUGGESTION".

    The suggestion (1) goes into the Solvable Rulebook, (2) is attached to the
    bug memory, and (3) is handed to the AI on the live call, which continues in
    real time (docs/architecture.md §2.6).
    """
    if not suggestion.strip():
        raise HumanActionError("suggestion is empty")
    with Session(engine, expire_on_commit=False) as s:
        bug = s.get(FirstTimeBug, bug_id)
        if not bug:
            raise HumanActionError("bug not found")
        if bug.status == "SUGGESTED":
            raise HumanActionError("this bug already has a suggestion")
        bug.status, bug.suggestion, bug.suggested_by, bug.resolved_at = "SUGGESTED", suggestion.strip(), operator, utcnow()
        s.add(bug)
        s.commit()
    ticket_id = bug.ticket_id
    rulebook.add_rule(topic=bug.title, knowledge=suggestion.strip(), department=bug.department,
                      source="first_time_bug_suggestion", ticket_id=ticket_id)
    memory.attach_bug_suggestion(ticket_id, suggestion.strip())
    row = _log(ticket_id, "TEACH", f"Suggestion for first-time bug: {suggestion.strip()}", previous="No precedent — flagged as first-time bug",
               reason="First-time bug suggestion", operator=operator)
    _guidance(ticket_id, suggestion.strip())
    tickets.update(ticket_id, needs_human=False, status="ACTIVE", next_step="Caller to try the suggested fix")
    tickets.add_event(ticket_id, operator, "HUMAN_TEACHING", f"Suggestion entered for first-time bug: {suggestion.strip()}",
                      status="COMPLETED", public="Our team shared a fix")
    learning_service.record(ticket_id, "First-time bug suggestion", source_event="FIRST_TIME_BUG", expected="Unknown — no precedent",
                            observed=suggestion.strip(), description="Suggestion written into the Solvable Rulebook and bug memory")
    hub.to_ops({"type": "bug_update", "bug": tickets.bug_dict(bug)})
    await _resume_safely(ticket_id, "suggestion", {"suggestion": suggestion.strip()})
    return row
