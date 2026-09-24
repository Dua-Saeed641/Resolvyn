"""spec §37-38: CORRECT replaces the AI's decision (and teaches the
rulebook); OVERRIDE hands control to the human outright. Both must reach a
valid outcome without restarting the whole graph."""

import uuid

from app.services import ticket_service as tickets

from .conftest import new_orchestrator, run_async


def _new_ticket(customer_id: str, text: str):
    t = tickets.create(uuid.uuid4().hex, channel="Text", customer_id=customer_id)
    tickets.update(t.ticket_id, body=text, subject=text[:140])
    return t.ticket_id


def test_correct_replaces_ai_decision_and_updates_rulebook():
    ticket_id = _new_ticket("CUS-20481", "I was charged twice for the same order ORD-83921 and want a refund.")

    async def scenario():
        async with new_orchestrator() as orch:
            start = await orch.start(ticket_id, tickets.get(ticket_id).body)
            assert start["paused"] is True

            result = await orch.resume(ticket_id, {
                "action": "CORRECT",
                "correction": "Do not refund automatically — verify with the payment gateway first, then process manually.",
                "operator": "Test Operator",
                "reason": "Amount is unusually high for an auto-flagged duplicate",
            })
            assert result["outcome"] == "RESOLVED"
            assert result["human_action"]["action"] == "CORRECT"
            assert result["learning_signal_id"] is not None

        detail = tickets.detail(ticket_id)
        corrections = [a for a in detail["human_actions"] if a["event_type"] == "CORRECTION"]
        assert len(corrections) == 1
        signals = [s for s in tickets.detail(ticket_id)["human_actions"]]  # sanity: still queryable
        assert signals

    run_async(scenario())


def test_override_takes_control_and_resolves():
    ticket_id = _new_ticket("CUS-20481", "I was charged twice for the same order ORD-83921 and want a refund.")

    async def scenario():
        async with new_orchestrator() as orch:
            await orch.start(ticket_id, tickets.get(ticket_id).body)
            result = await orch.resume(ticket_id, {
                "action": "OVERRIDE",
                "decision": "Handled the refund manually over the phone with the customer.",
                "operator": "Test Operator",
                "reason": "Customer needed same-call resolution",
            })
            assert result["human_action"]["action"] == "OVERRIDE"
            assert result["outcome"] == "RESOLVED"

        detail = tickets.detail(ticket_id)
        takeovers = [a for a in detail["human_actions"] if a["event_type"] == "OVERRIDE"]
        assert len(takeovers) == 1 and takeovers[0]["operator"] == "Test Operator"

    run_async(scenario())


def test_correct_and_override_are_distinct_ai_decision_vs_human_decision():
    """spec §38: 'AI plan != human action' — the human's chosen action, not
    the AI's original plan, is what the graph carries forward."""
    ticket_id = _new_ticket("CUS-20481", "I was charged twice for the same order ORD-83921 and want a refund.")

    async def scenario():
        async with new_orchestrator() as orch:
            await orch.start(ticket_id, tickets.get(ticket_id).body)
            result = await orch.resume(ticket_id, {
                "action": "OVERRIDE", "decision": "Escalated to legal instead of refunding.",
                "operator": "Test Operator", "reason": "Suspected fraud",
            })
            assert "legal" in result["customer_response"].lower()

        detail = tickets.detail(ticket_id)
        assert not any(c["tool_name"] == "issue_refund" and c["status"] == "COMPLETED" for c in detail["tool_calls"])

    run_async(scenario())
