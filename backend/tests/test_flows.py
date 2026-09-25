"""End-to-end flows over the real WebSocket, with no language model (deterministic playbooks)."""

import time

from app.vocab import TICKET_STATUSES


def _turn(ws, text: str, timeout: float = 30.0) -> list[dict]:
    """Send one caller utterance; collect events until the agent (or side-talk) finishes."""
    ws.send_json({"type": "utterance", "text": text})
    events, end = [], time.time() + timeout
    while time.time() < end:
        ev = ws.receive_json()
        events.append(ev)
        if ev["type"] in ("agent_done", "side_talk"):
            return events
    raise AssertionError(f"no reply to {text!r}")


def _said(events: list[dict]) -> str:
    return " ".join(e["text"] for e in events if e["type"] == "agent_sentence")


def _open(client, customer_id: str):
    ws = client.websocket_connect(f"/ws/call?channel=Text&customer_id={customer_id}")
    ctx = ws.__enter__()
    first = ctx.receive_json()
    while first["type"] != "session":
        first = ctx.receive_json()
    while True:  # greeting
        ev = ctx.receive_json()
        if ev["type"] == "agent_done":
            break
    return ws, ctx, first["ticket_id"]


def test_duplicate_payment_refund_needs_and_gets_human_approval(client):
    client.post("/api/demo/reset")
    ws, c, tid = _open(client, "CUS-20481")
    try:
        # a known caller does not have to read out an order ID: the desk finds the order with the duplicate charge itself
        first = _said(_turn(c, "Hi, I was charged twice for the same order and want a refund."))
        assert "2,499" in first and "83921" in first.replace("-", "")

        # The refund is over the auto-approval limit: it must wait for a human, not be claimed as done.
        reply = _said(_turn(c, "Yes please refund the duplicate one."))
        assert "nothing is refunded yet" in reply.lower() or "approve" in reply.lower()
        t = client.get(f"/api/tickets/{tid}").json()
        assert t["status"] == "WAITING_FOR_HUMAN"
        pending = [a for a in t["pending_actions"] if a["status"] == "PENDING"]
        assert len(pending) == 1 and pending[0]["params"]["amount"] == 2499
        assert client.get("/api/human-intelligence/approvals").json()[0]["ticket_id"] == tid

        # The manager approves: the AI executes, verifies, then tells the caller unprompted.
        r = client.post("/api/human-intelligence/approve", json={"ticket_id": tid, "action_id": pending[0]["action_id"], "reason": "verified"})
        assert r.status_code == 200
        events = []
        while not any(e["type"] == "agent_done" for e in events):
            events.append(c.receive_json())
        said = _said(events)
        assert "RFD-28192" in said and "verified" in said.lower() or "confirmed" in said.lower()

        t = client.get(f"/api/tickets/{tid}").json()
        tools = [(x["tool_name"], x["status"]) for x in t["tool_calls"]]
        assert ("issue_refund", "COMPLETED") in tools and ("verify_refund", "COMPLETED") in tools
        assert any(h["event_type"] == "APPROVAL" for h in t["human_actions"])
        assert any(s["signal_type"] == "Human approval" for s in client.get("/api/learning-signals").json())

        _turn(c, "Thanks, that's all.")
    finally:
        c.send_json({"type": "end"})
        ws.__exit__(None, None, None)
    time.sleep(1.5)
    t = client.get(f"/api/tickets/{tid}").json()
    assert t["status"] == "RESOLVED" and t["handled_by"] == "AI"
    assert t["resolution_path"] == "ACTION" and t["assigned_agent"] == "Billing"
    assert t["one_line_summary"] and t["detailed_summary"]
    assert t["jira_key"] == f"RSV-{tid.split('-')[1]}"
    assert all(e["status"] in (None, "WAITING", "COMPLETED", "FAILED", "NEW") for e in t["events"])
    assert t["status"] in TICKET_STATUSES


def test_side_talk_is_ignored_and_kept_out_of_the_ticket(client):
    ws, c, tid = _open(client, "CUS-20517")
    try:
        _turn(c, "Hi, I want to know where my order ORD-84155 is.")
        ev = _turn(c, "Mom, can you turn the TV down a little? I'm on the phone.")
        assert ev[-1]["type"] == "side_talk" and not any(e["type"] == "agent_sentence" for e in ev)
    finally:
        c.send_json({"type": "end"})
        ws.__exit__(None, None, None)
    t = client.get(f"/api/tickets/{tid}").json()
    kinds = {m["content"]: m["kind"] for m in t["messages"]}
    assert kinds["Mom, can you turn the TV down a little? I'm on the phone."] == "side_talk"
    assert any(e["event_type"] == "SIDE_TALK_DETECTED" for e in t["events"])


def test_first_time_bug_flags_manager_and_feeds_the_ai(client):
    ws, c, tid = _open(client, "CUS-20481")
    try:
        reply = _said(_turn(c, "My Studio Headphones show a flashing purple light and error code P-77 after the firmware update."))
        t = client.get(f"/api/tickets/{tid}").json()
        assert t["is_first_time_bug"] and t["status"] == "WAITING_FOR_HUMAN" and t["needs_human"]
        assert "flagged" in reply.lower() or "new one" in reply.lower()
        bugs = [b for b in client.get("/api/human-intelligence/bugs").json() if b["ticket_id"] == tid]
        assert bugs and bugs[0]["status"] == "OPEN"

        # No suggestion yet: the AI must not invent a fix.
        holding = _said(_turn(c, "I already tried charging them overnight."))
        assert "waiting" in holding.lower() or "team lead" in holding.lower()

        suggestion = "Hold the power button for fifteen seconds to force recovery mode, then charge until the light is white."
        r = client.post(f"/api/human-intelligence/bugs/{bugs[0]['bug_id']}/suggest", json={"suggestion": suggestion})
        assert r.status_code == 200
        events = []
        while not any(e["type"] == "agent_done" for e in events):
            events.append(c.receive_json())
        assert "fifteen seconds" in _said(events)

        # The suggestion is now part of the Solvable Rulebook, for next time.
        book = client.get("/api/knowledge/rulebook/by-department").json()
        assert any(r["source"] == "first_time_bug_suggestion" and "fifteen seconds" in r["knowledge"] for r in book["Technical"]["rules"])
        assert client.get(f"/api/tickets/{tid}").json()["status"] == "ACTIVE"

        _turn(c, "It worked, the light is white now. Thanks!")
    finally:
        c.send_json({"type": "end"})
        ws.__exit__(None, None, None)
    time.sleep(1.0)
    assert client.get(f"/api/tickets/{tid}").json()["status"] == "RESOLVED"


def test_second_caller_with_same_problem_is_answered_from_memory(client):
    """After a human taught the AI, the same problem is no longer a first-time bug."""
    ws, c, tid = _open(client, "CUS-20481")
    try:
        reply = _said(_turn(c, "My Studio Headphones show a flashing purple light and error code P-77 after the firmware update."))
        t = client.get(f"/api/tickets/{tid}").json()
        assert not t["is_first_time_bug"]
        assert "fifteen seconds" in reply or "power button" in reply.lower()
    finally:
        c.send_json({"type": "end"})
        ws.__exit__(None, None, None)


def test_asking_for_a_human_escalates_in_real_time(client):
    ws, c, tid = _open(client, "CUS-20481")
    try:
        _turn(c, "This is ridiculous, my order is late again and I want to speak to a manager right now!")
        t = client.get(f"/api/tickets/{tid}").json()
        assert t["escalated"] and t["needs_human"] and t["status"] == "WAITING_FOR_HUMAN"
        assert t["priority"] in ("HIGH", "CRITICAL") and t["sentiment"] == "Angry"
        assert t["assignee"] and "team" in t["assignee"]
    finally:
        c.send_json({"type": "end"})
        ws.__exit__(None, None, None)
    time.sleep(1.0)
    t = client.get(f"/api/tickets/{tid}").json()
    assert t["context_doc"] and "Context document created" in " ".join(e["description"] for e in t["events"])
    # The customer-facing view must not leak the internal summary or confidence.
    view = client.get(f"/api/tickets/{tid}/customer-view").json()
    assert "one_line_summary" not in view and "confidence" not in view


def test_simulated_api_outage_is_retried(client):
    assert client.post("/api/demo/fail-next/get_payment_transactions").status_code == 200
    ws, c, tid = _open(client, "CUS-20481")
    try:
        _turn(c, "I was charged twice, the order ID is ORD-83921.")
        t = client.get(f"/api/tickets/{tid}").json()
        assert any("retrying" in e["description"] for e in t["events"])
        assert ("get_payment_transactions", "COMPLETED") in [(x["tool_name"], x["status"]) for x in t["tool_calls"]]
    finally:
        c.send_json({"type": "end"})
        ws.__exit__(None, None, None)


def test_reset_demo_clears_live_state(client):
    assert client.post("/api/demo/reset").status_code == 200
    ids = [t["ticket_id"] for t in client.get("/api/tickets").json()]
    assert all(int(i.split("-")[1]) < 1042 for i in ids)
    assert client.get("/api/human-intelligence/bugs").json() == []


def test_demo_mode_runs_a_scripted_caller_through_the_real_pipeline(client):
    client.post("/api/demo/reset")
    before = {t["ticket_id"] for t in client.get("/api/tickets").json()}
    r = client.post("/api/demo/run/duplicate_payment?auto_human=true")
    assert r.status_code == 200 and r.json()["started"]
    deadline = time.time() + 60
    ticket = None
    while time.time() < deadline:
        mine = [t for t in client.get("/api/tickets").json()
                if t["ticket_id"] not in before and t["customer_name"] == "Lovekesh Anand" and t["status"] == "RESOLVED"]
        if mine:
            ticket = mine[0]
            break
        time.sleep(1)
    assert ticket, "demo ticket did not resolve"
    detail = client.get(f"/api/tickets/{ticket['ticket_id']}").json()
    assert any(h["operator"].endswith("(demo)") for h in detail["human_actions"])
    assert ("verify_refund", "COMPLETED") in [(c["tool_name"], c["status"]) for c in detail["tool_calls"]]


def test_ingested_documents_are_used_to_answer_and_shape_routing(client):
    """A manager's own SOP + product sheet become answerable knowledge, routed to the right department."""
    r = client.post("/api/knowledge/ingest-text", json={
        "title": "Store pickup SOP", "kind": "sop",
        "text": "# Store pickup\nCustomers can collect online orders from any store. Orders are held for 5 days. Bring the order ID and a photo ID.\n",
    })
    assert r.status_code == 200
    csv_row = b"sku,name,price_inr,warranty\nNV-SPK-05,Portable Speaker Mini,1799,1 year\n"
    r = client.post("/api/knowledge/ingest", files={"files": ("products.csv", csv_row)}, data={"kind": "product_db"})
    assert r.status_code == 200 and r.json()["ingested"][0]["departments"] == {"Other": 1}  # product data is shared

    ws, c, tid = _open(client, "CUS-20517")
    try:
        _turn(c, "Can I pick up my online order from the store?")
        t = client.get(f"/api/tickets/{tid}").json()
        assert not t["is_first_time_bug"] and t["resolution_path"] == "INSTANT"
        assert any("pickup" in k["title"].lower() for k in t["knowledge"])
        _turn(c, "How much does the Portable Speaker Mini cost?")
        t = client.get(f"/api/tickets/{tid}").json()
        assert not t["is_first_time_bug"]
    finally:
        c.send_json({"type": "end"})
        ws.__exit__(None, None, None)
