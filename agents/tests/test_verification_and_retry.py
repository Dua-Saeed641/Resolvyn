"""spec §40 (retry) and §41 (verification failure — mandatory): a tool that
fails must be retried within a bound, and a verification that never
succeeds must never let the ticket become RESOLVED or the customer
response claim success.
"""

import uuid
from unittest.mock import patch

from app.services import ticket_service as tickets
from app.tools.mock_apis import ApiUnavailable

from .conftest import new_orchestrator, run_async

# tool_service.REGISTRY captures a direct reference to each mock_apis function
# at import time (backend/app/tools/tool_service.py) — patching the attribute
# on `mock_apis` itself does not reach it, so tests patch the registry entry.
REGISTRY_PATCH_TARGET = "app.tools.tool_service.REGISTRY"


def _new_ticket(customer_id: str, text: str):
    t = tickets.create(uuid.uuid4().hex, channel="Text", customer_id=customer_id)
    tickets.update(t.ticket_id, body=text, subject=text[:140])
    return t.ticket_id


def test_transient_verification_failure_recovers_via_graph_retry():
    """verify_refund fails exactly once (tool_service's own internal retry
    absorbs it), so the run should still resolve — this documents that the
    existing tool-level retry (backend/app/tools/tool_service.py) and the
    graph's own retry_count are two independent, stacking layers."""
    ticket_id = _new_ticket("CUS-20481", "I was charged twice for the same order ORD-83921 and want a refund.")
    calls = {"n": 0}
    from app.tools import mock_apis

    real_verify = mock_apis.verify_refund

    def flaky(*a, **kw):
        calls["n"] += 1
        if calls["n"] == 1:
            raise ApiUnavailable("verify_refund: simulated outage")
        return real_verify(*a, **kw)

    from app.tools import tool_service

    async def scenario():
        with patch.dict(tool_service.REGISTRY, {"verify_refund": flaky}):
            async with new_orchestrator() as orch:
                await orch.start(ticket_id, tickets.get(ticket_id).body)
                result = await orch.resume(ticket_id, {"action": "APPROVE", "approve": True, "operator": "Test Operator"})
                assert result["outcome"] == "RESOLVED"
                assert result["action_verified"] is True

    run_async(scenario())
    assert calls["n"] >= 2  # tool_service's own attempt + at least one recovery


def test_persistent_verification_failure_never_claims_success():
    ticket_id = _new_ticket("CUS-20481", "I was charged twice for the same order ORD-83921 and want a refund.")

    def always_down(*a, **kw):
        raise ApiUnavailable("verify_refund: permanently down")

    from app.tools import tool_service

    async def scenario():
        with patch.dict(tool_service.REGISTRY, {"verify_refund": always_down}):
            async with new_orchestrator() as orch:
                await orch.start(ticket_id, tickets.get(ticket_id).body)
                result = await orch.resume(ticket_id, {"action": "APPROVE", "approve": True, "operator": "Test Operator"})

                # Whatever state the graph lands in (retried and re-gated, or
                # finally given up), it must never claim the refund succeeded.
                assert result.get("outcome") != "RESOLVED"
                response = result.get("customer_response") or ""
                assert "verified" not in response.lower() and "confirmed" not in response.lower()

        ticket = tickets.get(ticket_id)
        assert ticket.status != "RESOLVED"
        detail = tickets.detail(ticket_id)
        verify_calls = [c for c in detail["tool_calls"] if c["tool_name"] == "verify_refund"]
        assert verify_calls and all(c["status"] == "FAILED" for c in verify_calls)

    run_async(scenario())
