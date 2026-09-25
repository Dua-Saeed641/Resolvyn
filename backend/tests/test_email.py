"""The email channel: same pipeline as a call, replies as emails, threads, the approval follow-up, escalation."""

import time

from app.services.email_service import clean_body


def _send(client, sender, subject, text, ticket_id=None):
    body = {"from": sender, "subject": subject, "text": text}
    if ticket_id:
        body["ticket_id"] = ticket_id
    r = client.post("/api/email/inbound", json=body)
    assert r.status_code == 200, r.text
    return r.json()


def test_quoted_thread_and_signature_are_ignored():
    body = "Yes please refund it.\n\nThanks\n\nOn Mon, 21 Sep 2026 at 10:00, Riya <support@nova> wrote:\n> Want me to refund the duplicate?"
    assert clean_body(body) == "Yes please refund it. Thanks"
    assert clean_body("Where is my order?\n--\nSent from my iPhone") == "Where is my order?"


def test_known_customer_email_gets_a_real_answer_from_the_order_desk(client):
    out = _send(client, "Lovekesh Anand <lovekesh.anand@example.com>", "Order not here yet", "Hi, where is my order ORD-84102? It's late.")
    reply = out["reply"]
    assert reply and reply["to"] == "lovekesh.anand@example.com"
    assert reply["subject"] == f"Re: Order not here yet [{out['ticket_id']}]"
    assert reply["body"].startswith("Hi Lovekesh,") and "Ticket " + out["ticket_id"] in reply["body"]
    assert "delayed" in reply["body"].lower() or "nagpur" in reply["body"].lower()
    assert "umm" not in reply["body"].lower()
    t = client.get(f"/api/tickets/{out['ticket_id']}").json()
    assert t["channel"] == "Email" and t["customer_name"] == "Lovekesh Anand" and t["assigned_agent"] == "Order"
    assert not t["call_active"]


def test_a_thread_continues_and_the_approved_refund_is_emailed_unprompted(client):
    client.post("/api/demo/reset")
    first = _send(client, "lovekesh.anand@example.com", "Charged twice", "I was charged twice for my earbuds order. Please check.")
    tid = first["ticket_id"]
    assert "2,499" in first["reply"]["body"]
    # the customer replies in the same thread (the subject carries the ticket number)
    second = _send(client, "lovekesh.anand@example.com", first["reply"]["subject"], "Yes, please refund the duplicate one.\n\nOn Mon Riya wrote:\n> Want me to refund it?")
    assert second["ticket_id"] == tid
    assert "approv" in second["reply"]["body"].lower() or "nothing" in second["reply"]["body"].lower()
    t = client.get(f"/api/tickets/{tid}").json()
    act = next(a for a in t["pending_actions"] if a["status"] == "PENDING")
    client.post("/api/human-intelligence/approve", json={"ticket_id": tid, "action_id": act["action_id"], "reason": "ok"})
    end = time.time() + 10
    follow = []
    while time.time() < end and not follow:
        follow = [m for m in client.get("/api/email/outbox").json() if m["ticket_id"] == tid and "RFD-" in m["body"]]
        time.sleep(0.3)
    assert follow, "after the manager approves, Riya emails the verified refund on her own"
    thread = client.get(f"/api/email/thread/{tid}").json()
    assert [m["incoming"] for m in thread][:2] == [True, False] and len(thread) >= 5


def test_unknown_sender_is_a_guest_and_asking_for_a_manager_escalates(client):
    out = _send(client, "someone@unknown.example", "Complaint", "I want to speak to a manager about my order.")
    t = client.get(f"/api/tickets/{out['ticket_id']}").json()
    assert t["escalated"] and t["customer_id"] is None and t["channel"] == "Email"
    assert out["reply"] and out["reply"]["body"].startswith("Hi there,")


def test_webhook_form_post_works_like_an_inbound_parse_service(client):
    r = client.post("/api/email/inbound", data={"from": "Dua <dua.saeed@example.com>", "subject": "locked out", "text": "My account is locked, I can't log in."})
    assert r.status_code == 200 and r.json()["reply"]["to"] == "dua.saeed@example.com"


def test_empty_email_is_rejected(client):
    r = client.post("/api/email/inbound", json={"from": "a@b.c", "subject": "x", "text": "> only a quote"})
    assert r.status_code == 400


def _run_call(client, customer_id, lines):
    from tests.test_flows import _open, _turn
    ws, c, tid = _open(client, customer_id)
    for line in lines:
        _turn(c, line)
    return ws, c, tid


def _summaries(client, tid):
    return [m for m in client.get("/api/email/outbox").json() if m["ticket_id"] == tid and m["kind"] == "summary"]


def _wait_for(pred, timeout=12):
    end = time.time() + timeout
    while time.time() < end:
        v = pred()
        if v:
            return v
        time.sleep(0.3)
    return None


def test_after_a_resolved_call_the_customer_is_emailed_a_summary_with_the_verified_details(client):
    client.post("/api/demo/reset")
    ws, c, tid = _run_call(client, "CUS-20481", ["I was charged twice for my earbuds order", "yes please refund the duplicate one"])
    act = next(a for a in client.get(f"/api/tickets/{tid}").json()["pending_actions"] if a["status"] == "PENDING")
    client.post("/api/human-intelligence/approve", json={"ticket_id": tid, "action_id": act["action_id"], "reason": "ok"})
    from tests.test_flows import _turn
    _wait_for(lambda: client.get(f"/api/tickets/{tid}").json()["status"] == "VERIFYING")
    _turn(c, "great, thanks a lot, that's all") if False else c.send_json({"type": "utterance", "text": "great, thanks a lot, that's all"})
    mail = _wait_for(lambda: (_summaries(client, tid) or [None])[0])
    ws.__exit__(None, None, None)
    assert mail, "a summary email is sent once the ticket is resolved"
    assert mail["to"] == "lovekesh.anand@example.com" and f"[{tid}]" in mail["subject"]
    assert "RFD-" in mail["body"] and "2,499" in mail["body"] and "Status: Resolved" in mail["body"]
    assert "Hi Lovekesh," in mail["body"] and tid in mail["body"]
    assert len(_summaries(client, tid)) == 1, "one summary per outcome"


def test_an_escalated_call_gets_a_hand_over_summary(client):
    ws, c, tid = _run_call(client, "CUS-20517", ["Can you cancel my order ORD-84155? Actually, I want to speak to a manager"])
    mail = _wait_for(lambda: (_summaries(client, tid) or [None])[0])
    ws.__exit__(None, None, None)
    assert mail and "passed this to" in mail["body"] and mail["to"] == "dua.saeed@example.com"


def test_a_guest_without_an_email_gets_no_summary(client):
    client.post("/api/demo/reset")
    from tests.test_order_desk import _open_guest
    from tests.test_flows import _turn
    ws, c, tid = _open_guest(client)
    _turn(c, "I want to speak to a manager about a delivery problem")
    ws.__exit__(None, None, None)
    _wait_for(lambda: any(e["event_type"] == "SUMMARY_SKIPPED" for e in client.get(f"/api/tickets/{tid}").json()["events"]))
    assert not _summaries(client, tid)


def test_redirect_delivers_everything_to_one_inbox_and_names_the_intended_customer(client, monkeypatch):
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "email_redirect_to", "me@example.org")
    r = client.post("/api/email/test", json={"to": "someone@else.com"}).json()
    assert r["to"] == "me@example.org" and r["intended_for"] == "someone@else.com"
    box = client.get("/api/email/outbox").json()[0]
    assert box["to"] == "me@example.org" and "addressed to someone@else.com" in box["body"]


def test_a_customers_email_can_be_changed_and_is_used(client):
    r = client.patch("/api/customers/CUS-20517/email", json={"email": "dua.real@example.org"})
    assert r.status_code == 200 and r.json()["email"] == "dua.real@example.org"
    assert client.patch("/api/customers/CUS-20517/email", json={"email": "nonsense"}).status_code == 400
    client.patch("/api/customers/CUS-20517/email", json={"email": "dua.saeed@example.com"})
