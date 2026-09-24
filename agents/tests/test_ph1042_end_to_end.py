"""spec §36: the first fully tested graph path — PH-1042, duplicate payment,
through human approval to a verified, resolved ticket."""

import uuid

from app.services import ticket_service as tickets

from .conftest import new_orchestrator, run_async


def _new_ticket(customer_id: str, text: str):
    t = tickets.create(uuid.uuid4().hex, channel="Text", customer_id=customer_id)
    tickets.update(t.ticket_id, body=text, subject=text[:140])
    return t.ticket_id


def test_duplicate_payment_reaches_human_approval_gate():
    async def scenario():
        ticket_id = _new_ticket("CUS-20481", "I was charged twice for the same order ORD-83921 and want a refund.")
        async with new_orchestrator() as orch:
            result = await orch.start(ticket_id, tickets.get(ticket_id).body)

            assert result["paused"] is True
            assert result["decision_path"] == "ACTION"
            assert result["selected_agent"] == "Billing"
            gate = result["pending_human_gate"]
            assert gate["reason"] == "approval"
            assert gate["pending_action_id"] is not None

            ticket = tickets.get(ticket_id)
            assert ticket.status == "WAITING_FOR_HUMAN"
            pending = [p for p in tickets.detail(ticket_id)["pending_actions"] if p["status"] == "PENDING"]
            assert len(pending) == 1
            assert pending[0]["params"]["amount"] == 2499

    run_async(scenario())


def test_approval_executes_verifies_and_resolves():
    async def scenario():
        ticket_id = _new_ticket("CUS-20481", "I was charged twice for the same order ORD-83921 and want a refund.")
        async with new_orchestrator() as orch:
            await orch.start(ticket_id, tickets.get(ticket_id).body)
            result = await orch.resume(ticket_id, {"action": "APPROVE", "approve": True, "operator": "Test Operator"})

            assert result["paused"] is False
            assert result["action_executed"] is True
            assert result["action_verified"] is True
            assert result["outcome"] == "RESOLVED"
            assert "RFD-" in result["customer_response"]
            assert "verified" in result["customer_response"].lower() or "confirmed" in result["customer_response"].lower()
            assert result["learning_signal_id"] is not None

            ticket = tickets.get(ticket_id)
            assert ticket.status == "RESOLVED"

            detail = tickets.detail(ticket_id)
            tool_names = [c["tool_name"] for c in detail["tool_calls"]]
            assert "issue_refund" in tool_names and "verify_refund" in tool_names
            assert all(c["status"] == "COMPLETED" for c in detail["tool_calls"] if c["tool_name"] in ("issue_refund", "verify_refund"))

            approvals = [a for a in detail["human_actions"] if a["event_type"] == "APPROVAL"]
            assert len(approvals) == 1 and approvals[0]["operator"] == "Test Operator"

    run_async(scenario())


def test_rejection_does_not_resolve_or_refund():
    async def scenario():
        ticket_id = _new_ticket("CUS-20481", "I was charged twice for the same order ORD-83921 and want a refund.")
        async with new_orchestrator() as orch:
            await orch.start(ticket_id, tickets.get(ticket_id).body)
            result = await orch.resume(ticket_id, {"action": "APPROVE", "approve": False, "operator": "Test Operator",
                                                   "reason": "policy exception not granted"})

            assert result["outcome"] != "RESOLVED"
            detail = tickets.detail(ticket_id)
            assert not any(c["tool_name"] == "issue_refund" and c["status"] == "COMPLETED" for c in detail["tool_calls"])
            assert "not" in result["customer_response"].lower() or "sorry" in result["customer_response"].lower()

    run_async(scenario())
