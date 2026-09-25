"""Escalation edge cases: when the AI must hand over, when it must not, and what the hand-over carries."""

import time

from tests.test_flows import _open, _said, _turn


def _guest(client):
    ws = client.websocket_connect("/ws/call?channel=Text")
    c = ws.__enter__()
    first = c.receive_json()
    while first["type"] != "session":
        first = c.receive_json()
    while c.receive_json()["type"] != "agent_done":
        pass
    return ws, c, first["ticket_id"]


def _ticket(client, tid):
    return client.get(f"/api/tickets/{tid}").json()


def _escalations(t):
    return [e for e in t["events"] if e["event_type"] == "ESCALATED"]


def _wait(pred, timeout=8.0):
    end = time.time() + timeout
    while time.time() < end:
        if pred():
            return True
        time.sleep(0.2)
    return False


def test_asking_for_a_manager_first_thing_escalates_and_asks_what_the_team_needs(client):
    ws, c, tid = _guest(client)
    try:
        reply = _said(_turn(c, "I want to speak to a manager right now"))
        t = _ticket(client, tid)
        assert t["escalated"] and t["status"] == "WAITING_FOR_HUMAN" and t["assignee"]
        assert "name" in reply.lower(), "a guest is asked for their name so the teammate has it"
    finally:
        ws.__exit__(None, None, None)


def test_asking_twice_does_not_escalate_twice(client):
    ws, c, tid = _open(client, "CUS-20481")
    try:
        _turn(c, "Where is my order ORD-84102?")
        _turn(c, "I want to talk to a manager")
        _turn(c, "Can I please speak to a manager?")
        assert len(_escalations(_ticket(client, tid))) == 1
    finally:
        ws.__exit__(None, None, None)


def test_hinglish_request_for_a_person_escalates(client):
    ws, c, tid = _guest(client)
    try:
        _turn(c, "mujhe manager se baat karni hai")
        assert _ticket(client, tid)["escalated"]
    finally:
        ws.__exit__(None, None, None)


def test_saying_you_do_not_want_a_manager_does_not_escalate(client):
    ws, c, tid = _open(client, "CUS-20481")
    try:
        _turn(c, "Where is my order ORD-84102? I don't want to talk to a manager, just tell me")
        t = _ticket(client, tid)
        assert not t["escalated"] and t["assigned_agent"] == "Order"
    finally:
        ws.__exit__(None, None, None)


def test_angry_caller_unresolved_after_two_exchanges_is_escalated(client):
    ws, c, tid = _open(client, "CUS-20481")
    try:
        _turn(c, "This is ridiculous, my headphones keep disconnecting, this is the worst")
        assert not _ticket(client, tid)["escalated"], "one angry sentence is not enough"
        _turn(c, "This is unacceptable, it is still disconnecting, absolutely pathetic")
        t = _ticket(client, tid)
        assert t["escalated"] and "angry" in (t["escalation_reason"] or "").lower()
    finally:
        ws.__exit__(None, None, None)


def test_order_not_found_twice_escalates(client):
    ws, c, tid = _guest(client)
    try:
        _turn(c, "Hi, where is my order?")
        _turn(c, "it's ORD-11111")
        r = _said(_turn(c, "sorry, ORD-22222"))
        t = _ticket(client, tid)
        assert t["escalated"] and "teammate" in r.lower()
    finally:
        ws.__exit__(None, None, None)


def test_service_outage_after_retry_escalates_and_never_claims_success(client):
    client.post("/api/demo/reset")
    ws, c, tid = _open(client, "CUS-20481")
    try:
        client.post("/api/demo/fail-next/lookup_order?times=2")  # fails, and fails again on the automatic retry
        r = _said(_turn(c, "Where is my order ORD-84102?"))
        t = _ticket(client, tid)
        assert t["escalated"] or t["status"] == "WAITING_FOR_HUMAN"
        assert "delayed" not in r.lower() and "nagpur" not in r.lower()
    finally:
        ws.__exit__(None, None, None)


def test_escalation_while_a_refund_awaits_approval_keeps_the_approval(client):
    client.post("/api/demo/reset")
    ws, c, tid = _open(client, "CUS-20481")
    try:
        _turn(c, "I was charged twice for my order")
        _turn(c, "yes please refund the duplicate")
        _turn(c, "this is taking too long, let me talk to a manager")
        t = _ticket(client, tid)
        assert t["escalated"]
        assert any(a["status"] == "PENDING" for a in t["pending_actions"]), "the refund request must not be lost"
        # the manager can still approve and the refund is executed and verified
        act = next(a for a in t["pending_actions"] if a["status"] == "PENDING")
        client.post("/api/human-intelligence/approve", json={"ticket_id": tid, "action_id": act["action_id"], "reason": "ok"})
        assert _wait(lambda: any(x["tool_name"] == "verify_refund" and x["status"] == "COMPLETED" for x in _ticket(client, tid)["tool_calls"]))
    finally:
        ws.__exit__(None, None, None)


def test_hanging_up_after_escalation_leaves_the_ticket_with_the_team_and_a_context_document(client):
    ws, c, tid = _open(client, "CUS-20517")
    _turn(c, "Can I cancel order ORD-84155? Actually just get me a manager")
    ws.__exit__(None, None, None)
    assert _wait(lambda: bool(_ticket(client, tid)["context_doc"]))
    t = _ticket(client, tid)
    assert t["status"] == "WAITING_FOR_HUMAN" and t["escalated"] and not t["call_active"]


def test_after_a_human_takes_over_the_ai_stays_silent(client):
    ws, c, tid = _open(client, "CUS-20481")
    try:
        _turn(c, "Where is my order ORD-84102?")
        client.post("/api/human-intelligence/override", json={"ticket_id": tid, "decision": "I'll handle this", "reason": "test"})
        c.send_json({"type": "utterance", "text": "hello? are you there?"})
        time.sleep(1.5)
        t = _ticket(client, tid)
        assert t["messages"][-1]["sender"] == "CUSTOMER", "no AI reply after a human took over"
    finally:
        ws.__exit__(None, None, None)
