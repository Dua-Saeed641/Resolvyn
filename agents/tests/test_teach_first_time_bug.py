"""spec §18, §39: an issue with no precedent anywhere must be flagged as a
first-time bug, gated to a human, and resolved once TEACH writes a rule —
without ever claiming a retrained model."""

import uuid

from app.services import ticket_service as tickets

from .conftest import new_orchestrator, run_async

NOVEL_ISSUE = (
    "The ceremonial garden gnome my grandmother painted keeps whispering "
    "different stock tickers at midnight and I don't know what to do about it."
)
# A distinct second scenario for the TEACH-resolution test — reusing NOVEL_ISSUE
# would let this test's freshly-taught bug memory compete at retrieval time
# with the *other* test's still-unresolved bug entry for the same text,
# since both land in the same shared (session-scoped) test database.
NOVEL_ISSUE_2 = (
    "My neighbor's wind chime keeps playing the same three notes every time "
    "I water the ferns on Tuesdays and I have no idea why."
)


def _new_ticket(customer_id: str, text: str):
    t = tickets.create(uuid.uuid4().hex, channel="Text", customer_id=customer_id)
    tickets.update(t.ticket_id, body=text, subject=text[:140])
    return t.ticket_id


def test_novel_issue_is_flagged_as_first_time_bug():
    ticket_id = _new_ticket("CUS-20481", NOVEL_ISSUE)

    async def scenario():
        async with new_orchestrator() as orch:
            result = await orch.start(ticket_id, tickets.get(ticket_id).body)
            assert result["paused"] is True
            assert result["decision_path"] in ("FIRST_TIME_BUG", "KNOWN_OPEN_BUG")
            assert result["is_first_time_bug"] is True
            assert result["pending_human_gate"]["reason"] == "first_time_bug"

        ticket = tickets.get(ticket_id)
        assert ticket.status == "WAITING_FOR_HUMAN"
        assert ticket.is_first_time_bug is True
        detail = tickets.detail(ticket_id)
        assert len(detail["bugs"]) == 1 and detail["bugs"][0]["status"] == "OPEN"

    run_async(scenario())


def test_teach_resolves_the_bug_and_updates_the_rulebook():
    ticket_id = _new_ticket("CUS-20481", NOVEL_ISSUE_2)

    async def scenario():
        async with new_orchestrator() as orch:
            await orch.start(ticket_id, tickets.get(ticket_id).body)
            result = await orch.resume(ticket_id, {
                "action": "TEACH",
                "topic": "Wind chime plays three notes when watering ferns on Tuesdays",
                "knowledge": (
                    "The wind chime's magnetic clapper is picking up static from the plant-mister's "
                    "motor. Advise moving the chime at least two metres from the mister, or unplugging "
                    "the mister during watering — this stops the three-note pattern completely."
                ),
                "operator": "Test Operator",
            })

        assert result["outcome"] == "RESOLVED"
        assert result["learning_signal_id"] is not None

        from app.memory.rulebook import by_department
        rules = [r for dept in by_department().values() for r in dept
                if r["source"] == "first_time_bug_suggestion" and r["ticket_id"] == ticket_id]
        assert len(rules) == 1
        assert "mister" in rules[0]["knowledge"].lower()

        detail = tickets.detail(ticket_id)
        assert detail["bugs"][0]["status"] == "SUGGESTED"
        assert not any("retrain" in (a.get("human_action") or "").lower() for a in detail["human_actions"])

    run_async(scenario())
