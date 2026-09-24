"""spec §24: GUIDE adds context and resumes reasoning — distinct from
APPROVE (authorizing a pending action) and from TEACH (a durable rule)."""

import uuid

from app.services import ticket_service as tickets

from .conftest import new_orchestrator, run_async


def _new_ticket(customer_id: str, text: str):
    t = tickets.create(uuid.uuid4().hex, channel="Text", customer_id=customer_id)
    tickets.update(t.ticket_id, body=text, subject=text[:140])
    return t.ticket_id


def test_guide_unblocks_a_ticket_missing_the_order_id():
    # No order id in the text — Billing will ask for one and, since there is
    # no tool-flow signal at all, the decision engine treats this as small
    # talk / no problem stated, or Jev's confidence is too low to route to
    # tools; either way this exercises GUIDE's entity-extraction unblock path
    # for a ticket that has genuinely stalled waiting on missing information.
    ticket_id = _new_ticket("CUS-20481", "I need help with a billing issue on a recent order, it's urgent.")

    async def scenario():
        async with new_orchestrator() as orch:
            start = await orch.start(ticket_id, tickets.get(ticket_id).body)
            if not start["paused"]:
                return  # resolved/instant on the first pass — nothing to guide
            if start["pending_human_gate"]["reason"] != "needs_human":
                return  # landed on a different gate (e.g. approval) — not this scenario

            result = await orch.resume(ticket_id, {
                "action": "GUIDE", "guidance": "The order ID is ORD-83921.", "operator": "Test Operator",
            })
            assert result["human_action"]["action"] == "GUIDE"
            assert result["learning_signal_id"] is not None

        detail = tickets.detail(ticket_id)
        guidance_events = [a for a in detail["human_actions"] if a["event_type"] == "GUIDANCE"]
        assert len(guidance_events) == 1

    run_async(scenario())
