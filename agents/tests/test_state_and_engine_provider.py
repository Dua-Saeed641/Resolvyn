"""Unit tests (spec §43): state model + the deterministic engine provider,
with no graph execution involved."""

from app.agents.base_agent import TurnContext

from agents.engine_provider import DeterministicEngineProvider, judgment_dict, judgment_from_dict
from agents.state import new_state, public_state


def test_new_state_has_no_leaked_mutable_defaults():
    a = new_state("PH-0001", "hello")
    b = new_state("PH-0002", "world")
    a["trace"].append("X")
    assert b["trace"] == []  # each call gets its own list, not a shared one
    a["agent_state"]["k"] = "v"
    assert b["agent_state"] == {}


def test_public_state_drops_agent_scratch_space():
    state = new_state("PH-0001", "hello")
    state["agent_state"]["order_id"] = "ORD-1"
    state["decision_path"] = "ACTION"
    out = public_state(state)
    assert "agent_state" not in out
    assert out["decision_path"] == "ACTION"


def test_judgment_roundtrip_through_dict():
    provider = DeterministicEngineProvider()
    j = provider.judge("I was charged twice for my order and want a refund")
    d = judgment_dict(j)
    assert "extras" not in d
    restored = judgment_from_dict(d)
    assert restored.intent == j.intent
    assert restored.department == j.department
    assert restored.confidence == j.confidence


def test_perceive_extracts_order_id():
    provider = DeterministicEngineProvider()
    enriched = provider.perceive("my order is ORD-83921 and it's late", "Ticket")
    assert enriched["entities"].get("order_id") == "ORD-83921"


def test_retrieve_returns_a_retrieval_with_scores():
    provider = DeterministicEngineProvider()
    j = provider.judge("I was charged twice for my order and want a refund")
    query = provider.write_query("I was charged twice for my order and want a refund", j)
    ret = provider.retrieve(query, j.department)
    assert 0.0 <= ret.best_common <= 1.0
    assert 0.0 <= ret.best_bug <= 1.0


def test_reason_is_deterministic_without_a_model(seeded_db):
    provider = DeterministicEngineProvider()
    text = "I was charged twice for the same order ORD-83921 and want a refund."
    j = provider.judge(text)
    query = provider.write_query(text, j)
    ret = provider.retrieve(query, j.department, exclude_ticket=None)
    ctx = TurnContext(session=None, ticket_id="PH-TEST", text=text, entities={"order_id": "ORD-83921"},
                      judgment=j, retrieval=ret, customer=None, state={"order_id": "ORD-83921"}, language="en")
    import asyncio

    decision = asyncio.run(provider.reason(ctx))
    assert decision.path in ("ACTION", "INSTANT", "FIRST_TIME_BUG", "KNOWN_OPEN_BUG", "ESCALATED")
