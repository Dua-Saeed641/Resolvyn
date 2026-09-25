"""agents/swarm_router.py — the fruit-fly-inspired mixture-of-experts routing
stage. Covers the router in isolation (deterministic scoring, ambiguity,
expert failure) and wired into the real graph (sparse activation, GUIDE/
CORRECT/OVERRIDE reroute paths, learning signals, no duplicate events).

See docs/swarm-router.md for what this is (and is not) modelling.
"""

import uuid

import pytest
from sqlmodel import Session, select

from app.database import engine
from app.models import LearningSignal
from app.services import ticket_service as tickets
from app.vocab import DEPARTMENTS

from agents import swarm_router
from agents.swarm_router import SwarmRoutingError

from .conftest import new_orchestrator, run_async


def _new_ticket(customer_id: str, text: str):
    t = tickets.create(uuid.uuid4().hex, channel="Text", customer_id=customer_id)
    tickets.update(t.ticket_id, body=text, subject=text[:140])
    return t.ticket_id


# ── unit-level: the router in isolation ──────────────────────────────────────

DUPLICATE_PAYMENT = "I was charged twice for the same order ORD-83921 and want a refund."
ACCOUNT_LOCKED = "I am locked out of my account and cannot log in, my password reset is not working."
REFUND_NOT_RECEIVED = "I still have not received my refund, it has been pending for a week."
SHIPMENT_DELAYED = "Where is my order? It has not arrived and the delivery is late, still not here."
PRODUCT_NOT_WORKING = "The device stopped working, the app keeps crashing and it wont turn on."
AMBIGUOUS_TEXT = "My order has an app problem."
AMBIGUOUS_GUIDANCE = "The device itself is broken and wont turn on, its not an order tracking issue."


@pytest.mark.parametrize("text,expected", [
    (DUPLICATE_PAYMENT, "Billing"),
    (ACCOUNT_LOCKED, "Account"),
    (REFUND_NOT_RECEIVED, "Billing"),
    (SHIPMENT_DELAYED, "Order"),
    (PRODUCT_NOT_WORKING, "Technical"),
])
def test_swarm_picks_the_right_department(text, expected):
    result = swarm_router.evaluate("T-1", text=text)
    assert result.winner == expected
    assert not result.ambiguous


def test_shipment_delay_routes_to_order_not_logistics():
    """docs/claude.md: Logistics was retired from an earlier prototype roster;
    shipping/tracking belongs to Order, and Order is a real department — this
    must never come back as a 6th/renamed department."""
    result = swarm_router.evaluate("T-1", text=SHIPMENT_DELAYED)
    assert result.winner == "Order"
    assert {c.agent for c in result.candidates} == set(DEPARTMENTS)
    assert "Logistics" not in {c.agent for c in result.candidates}


def test_activation_scores_are_bounded():
    for text in (DUPLICATE_PAYMENT, ACCOUNT_LOCKED, AMBIGUOUS_TEXT, "hello there, just saying hi"):
        result = swarm_router.evaluate("T-1", text=text)
        for c in result.candidates:
            assert 0.0 <= c.activation_score <= 1.0
            assert 0.0 <= c.intent_match <= 1.0
            assert 0.0 <= c.domain_match <= 1.0


def test_routing_is_deterministic():
    r1 = swarm_router.evaluate("T-1", text=DUPLICATE_PAYMENT)
    r2 = swarm_router.evaluate("T-1", text=DUPLICATE_PAYMENT)
    assert [c.activation_score for c in r1.candidates] == [c.activation_score for c in r2.candidates]
    assert r1.winner == r2.winner
    assert r1.activation_gap == r2.activation_gap


def test_winner_runner_up_and_gap():
    result = swarm_router.evaluate("T-1", text=DUPLICATE_PAYMENT)
    assert result.winner == "Billing"
    assert result.winner_score > result.runner_up_score
    assert result.activation_gap == round(result.winner_score - result.runner_up_score, 4)
    assert result.runner_up is not None and result.runner_up != result.winner


def test_ambiguous_routing_is_detected_without_randomness():
    result = swarm_router.evaluate("T-1", text=AMBIGUOUS_TEXT)
    assert result.ambiguous is True
    assert result.activation_gap < swarm_router.DOMINANCE_MARGIN
    assert len(result.selected_experts) > 1  # top_k consultation, not a silent single guess
    assert result.winner in result.selected_experts and result.runner_up in result.selected_experts


def test_guidance_resolves_the_ambiguity_deterministically():
    combined = f"{AMBIGUOUS_TEXT} {AMBIGUOUS_GUIDANCE}"
    result = swarm_router.evaluate("T-1", text=combined)
    assert result.ambiguous is False
    assert result.winner == "Technical"


def test_expert_failure_is_recorded_and_excluded(monkeypatch):
    real = swarm_router._department_intent_score

    def flaky(dept, low_text):
        if dept == "Billing":
            raise RuntimeError("Billing's own scoring blew up")
        return real(dept, low_text)

    monkeypatch.setattr(swarm_router, "_department_intent_score", flaky)
    result = swarm_router.evaluate("T-1", text=DUPLICATE_PAYMENT)
    assert "Billing" in result.failed_experts
    assert result.winner != "Billing"  # a failed expert can never win
    assert len(result.candidates) == len(DEPARTMENTS)  # still reported, just excluded from ranking
    billing = next(c for c in result.candidates if c.agent == "Billing")
    assert billing.activation_score == 0.0


def test_all_experts_failing_raises_instead_of_a_silent_default(monkeypatch):
    def boom(dept, low_text):
        raise RuntimeError("scoring backend down")

    monkeypatch.setattr(swarm_router, "_department_intent_score", boom)
    with pytest.raises(SwarmRoutingError):
        swarm_router.evaluate("T-1", text=DUPLICATE_PAYMENT)


# ── integration: the router wired into the real graph ────────────────────────


def test_graph_activates_only_the_winning_department():
    ticket_id = _new_ticket("CUS-20481", DUPLICATE_PAYMENT)

    async def scenario():
        async with new_orchestrator() as orch:
            result = await orch.start(ticket_id, tickets.get(ticket_id).body)
            assert result["selected_agent"] == "Billing"
            assert result["swarm_winner"] == "Billing"
            assert result["swarm_ambiguous"] is False
            assert len(result["swarm_activations"]) == len(DEPARTMENTS)
            assert result["routing_reason"]

        ticket = tickets.get(ticket_id)
        assert ticket.assigned_agent == "Billing"
        detail = tickets.detail(ticket_id)
        assigned_events = [e for e in detail["events"] if e["event_type"] == "AGENT_ASSIGNED"]
        assert len(assigned_events) == 1  # exactly one routing decision per pass — no duplicates (spec §45)
        assert assigned_events[0]["meta"]["swarm"]["winner"] == "Billing"

    run_async(scenario())


def test_ambiguous_ticket_pauses_for_guide_then_reroutes():
    ticket_id = _new_ticket("CUS-20481", AMBIGUOUS_TEXT)

    async def scenario():
        async with new_orchestrator() as orch:
            start = await orch.start(ticket_id, tickets.get(ticket_id).body)
            assert start["paused"] is True
            assert start["swarm_ambiguous"] is True
            assert start["pending_human_gate"]["reason"] == "ambiguous_routing"

            ticket = tickets.get(ticket_id)
            assert ticket.status == "WAITING_FOR_HUMAN"

            result = await orch.resume(ticket_id, {
                "action": "GUIDE", "guidance": AMBIGUOUS_GUIDANCE, "operator": "Test Operator",
            })
            assert result["swarm_ambiguous"] is False
            assert result["selected_agent"] == "Technical"
            assert result["swarm_winner"] == "Technical"

        detail = tickets.detail(ticket_id)
        assigned_events = [e for e in detail["events"] if e["event_type"] == "AGENT_ASSIGNED"]
        assert len(assigned_events) == 2  # the ambiguous pass, then the guided re-route — both kept, not overwritten
        assert assigned_events[0]["meta"]["swarm"]["ambiguous"] is True
        assert assigned_events[1]["meta"]["swarm"]["winner"] == "Technical"

    run_async(scenario())


def test_correct_reroutes_to_a_different_department_and_learns():
    ticket_id = _new_ticket("CUS-20481", DUPLICATE_PAYMENT)

    async def scenario():
        async with new_orchestrator() as orch:
            start = await orch.start(ticket_id, tickets.get(ticket_id).body)
            assert start["selected_agent"] == "Billing"  # the AI's (correct-looking) original pick

            result = await orch.resume(ticket_id, {
                "action": "CORRECT", "department": "Technical",
                "correction": "This is actually a card-reader hardware fault, not a duplicate charge.",
                "operator": "Test Operator", "reason": "Misclassified by keyword match",
            })
            assert result["selected_agent"] == "Technical"
            assert result["human_action"]["rerouted"] is True

        ticket = tickets.get(ticket_id)
        assert ticket.assigned_agent == "Technical"

        detail = tickets.detail(ticket_id)
        # the original swarm decision is preserved, not erased (spec §26)
        assigned_events = [e for e in detail["events"] if e["event_type"] == "AGENT_ASSIGNED"]
        assert any(e["meta"]["swarm"]["winner"] == "Billing" for e in assigned_events)

        with Session(engine) as s:
            wrong_routing = s.exec(
                select(LearningSignal).where(LearningSignal.ticket_id == ticket_id,
                                             LearningSignal.signal_type == "Wrong agent routing")
            ).all()
        assert len(wrong_routing) == 1
        assert wrong_routing[0].expected_action == "Billing"
        assert wrong_routing[0].observed_action == "Technical"

    run_async(scenario())


def test_override_can_reassign_department_for_the_audit_trail():
    ticket_id = _new_ticket("CUS-20481", DUPLICATE_PAYMENT)

    async def scenario():
        async with new_orchestrator() as orch:
            start = await orch.start(ticket_id, tickets.get(ticket_id).body)
            assert start["selected_agent"] == "Billing"

            result = await orch.resume(ticket_id, {
                "action": "OVERRIDE", "department": "Account",
                "decision": "This is actually an account-security issue; handling directly.",
                "operator": "Test Operator", "reason": "Swarm misrouted",
            })
            assert result["human_action"]["department"] == "Account"
            assert result["outcome"] == "RESOLVED"

        ticket = tickets.get(ticket_id)
        assert ticket.assigned_agent == "Account"
        # Note: ticket.handled_by ends up "AI" here, not "HUMAN" — a pre-existing
        # quirk in agents/nodes.py::record_outcome (unconditionally sets
        # handled_by="AI" whenever outcome==RESOLVED, regardless of who actually
        # resolved it) that predates this feature and is out of scope here.

        with Session(engine) as s:
            wrong_routing = s.exec(
                select(LearningSignal).where(LearningSignal.ticket_id == ticket_id,
                                             LearningSignal.signal_type == "Wrong agent routing")
            ).all()
        assert len(wrong_routing) == 1 and wrong_routing[0].observed_action == "Account"

    run_async(scenario())


def test_correct_without_department_keeps_existing_behavior():
    """Backward compatibility: CORRECT with no `department` must behave exactly
    as before this feature existed (agents/tests/test_human_correct_override.py
    already covers this path — this is a narrower, swarm-specific check that no
    reroute/learning-signal side effect fires when department is omitted)."""
    ticket_id = _new_ticket("CUS-20481", DUPLICATE_PAYMENT)

    async def scenario():
        async with new_orchestrator() as orch:
            await orch.start(ticket_id, tickets.get(ticket_id).body)
            result = await orch.resume(ticket_id, {
                "action": "CORRECT", "correction": "Verify with the gateway before refunding.",
                "operator": "Test Operator",
            })
            assert result["human_action"].get("rerouted") in (None, False)

        ticket = tickets.get(ticket_id)
        assert ticket.assigned_agent == "Billing"  # unchanged

        with Session(engine) as s:
            wrong_routing = s.exec(
                select(LearningSignal).where(LearningSignal.ticket_id == ticket_id,
                                             LearningSignal.signal_type == "Wrong agent routing")
            ).all()
        assert len(wrong_routing) == 0

    run_async(scenario())
