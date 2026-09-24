"""spec §30, §42: resuming must never double-refund, double-log, or
double-notify. `mock_apis.issue_refund` is already idempotent per
(order_id, transaction_id) — this proves the graph relies on that rather
than re-deciding on every resume, and that repeated/duplicate resume
attempts are rejected rather than silently re-run."""

import uuid

from app.services import ticket_service as tickets

from .conftest import new_orchestrator, run_async


def _new_ticket(customer_id: str, text: str):
    t = tickets.create(uuid.uuid4().hex, channel="Text", customer_id=customer_id)
    tickets.update(t.ticket_id, body=text, subject=text[:140])
    return t.ticket_id


def test_resuming_a_completed_thread_is_rejected_not_replayed():
    from agents.service import OrchestrationError

    ticket_id = _new_ticket("CUS-20481", "I was charged twice for the same order ORD-83921 and want a refund.")

    async def scenario():
        async with new_orchestrator() as orch:
            await orch.start(ticket_id, tickets.get(ticket_id).body)
            first = await orch.resume(ticket_id, {"action": "APPROVE", "approve": True, "operator": "Test Operator"})
            assert first["outcome"] == "RESOLVED"

            try:
                await orch.resume(ticket_id, {"action": "APPROVE", "approve": True, "operator": "Test Operator (again)"})
                raised = False
            except OrchestrationError:
                raised = True
            assert raised, "a second resume on an already-completed thread must be rejected, not silently re-run"

        detail = tickets.detail(ticket_id)
        completed_refunds = [c for c in detail["tool_calls"] if c["tool_name"] == "issue_refund" and c["status"] == "COMPLETED"]
        assert len(completed_refunds) == 1  # exactly one refund, never two
        approvals = [a for a in detail["human_actions"] if a["event_type"] == "APPROVAL"]
        assert len(approvals) == 1  # exactly one approval logged, never two

    run_async(scenario())


def test_learning_signal_recorded_exactly_once_per_outcome():
    ticket_id = _new_ticket("CUS-20481", "I was charged twice for the same order ORD-83921 and want a refund.")

    async def scenario():
        async with new_orchestrator() as orch:
            await orch.start(ticket_id, tickets.get(ticket_id).body)
            await orch.resume(ticket_id, {"action": "APPROVE", "approve": True, "operator": "Test Operator"})

        from app.learning.learning_service import list_signals
        resolution_signals = [s for s in list_signals() if s["ticket_id"] == ticket_id and s["signal_type"] == "Successful resolution"]
        assert len(resolution_signals) == 1

    run_async(scenario())
