"""The order desk against the business database, replaying a real Hinglish call that went wrong."""

from tests.test_flows import _said, _turn


def _open_guest(client):
    ws = client.websocket_connect("/ws/call?channel=Text")
    c = ws.__enter__()
    first = c.receive_json()
    while first["type"] != "session":
        first = c.receive_json()
    while c.receive_json()["type"] != "agent_done":
        pass
    return ws, c, first["ticket_id"]


def test_order_question_in_hinglish_is_not_a_bug_and_bare_digits_are_an_order_id(client):
    ws, c, tid = _open_guest(client)
    try:
        r1 = _said(_turn(c, "hi mera naam mukesh hai aur mere ko apna order ke baare mein puchhana tha jo maine parson order kiya tha"))
        t = client.get(f"/api/tickets/{tid}").json()
        assert not t["is_first_time_bug"], "an order question is never a first-time bug"
        assert t["assigned_agent"] == "Order"
        assert t["customer_name"] == "Mukesh", "the name ends at 'hai'"
        assert "order" in r1.lower()

        r2 = _said(_turn(c, "ismein 3508 likha hua hai"))
        low = r2.lower()
        assert "already reported" not in low and "others" not in low and "team lead" not in low
        assert "3508" in r2 and "can't find" in low or "cannot find" in low
        t = client.get(f"/api/tickets/{tid}").json()
        assert not t["is_first_time_bug"] and t["order_id"] in (None, "ORD-3508")
    finally:
        ws.__exit__(None, None, None)


def test_last_digits_of_an_order_find_the_order(client):
    ws, c, tid = _open_guest(client)
    try:
        _turn(c, "Hi I want to check where my order is, my name is Lovekesh")
        reply = _said(_turn(c, "it's 8 3 9 2 1"))
        assert "earbuds" in reply.lower() or "blue" in reply.lower() or "transit" in reply.lower()
    finally:
        ws.__exit__(None, None, None)


def test_known_caller_needs_no_order_id(client):
    ws, c, tid = _open_guest(client)
    try:
        _turn(c, "Where is my order?")
        r = _said(_turn(c, "my registered email is dua.saeed@example.com"))
        assert "yoga" in r.lower() or "processing" in r.lower()
        assert client.get(f"/api/tickets/{tid}").json()["customer_name"] == "Dua Saeed"
    finally:
        ws.__exit__(None, None, None)


def test_business_data_is_a_real_database_and_takes_your_own_records(client):
    snap = client.get("/api/business/data").json()
    assert {o["order_id"] for o in snap["orders"]} >= {"ORD-83921", "ORD-84230"}
    assert any(p["transaction_id"] == "TXN-90113" for p in snap["payments"])

    csv = b"order_id,customer_id,item,amount,placed,status\nORD-3508,CUS-20481,Cotton Kurta,1499,2026-09-23,Shipped\n"
    r = client.post("/api/business/import", files={"file": ("orders.csv", csv, "text/csv")})
    assert r.status_code == 200 and r.json() == {"kind": "orders", "imported": 1}

    looked = client.get("/api/business/orders/lookup", params={"ref": "3508"}).json()
    assert looked["found"] and looked["order"]["item"] == "Cotton Kurta" and looked["match"] == "exact"
    looked = client.get("/api/business/orders/lookup", params={"ref": "508"}).json()
    assert looked["found"] and looked["match"] == "partial"
    assert not client.get("/api/business/orders/lookup", params={"ref": "99999"}).json()["found"]


def test_asking_whether_riya_is_a_bot_is_answered_honestly_not_escalated(client):
    ws, c, tid = _open_guest(client)
    try:
        reply = _said(_turn(c, "hi, are you a real person or a bot?"))
        assert "ai assistant" in reply.lower()
        t = client.get(f"/api/tickets/{tid}").json()
        assert not t["escalated"] and t["status"] != "WAITING_FOR_HUMAN"
    finally:
        ws.__exit__(None, None, None)


def test_unshipped_order_has_no_invented_delivery_date(client):
    ws, c, tid = _open_guest(client)
    try:
        _turn(c, "Where is my order?")
        reply = _said(_turn(c, "it is ORD-84155"))
        assert "hasn't shipped" in reply.lower() or "not shipped" in reply.lower()
    finally:
        ws.__exit__(None, None, None)


def test_invented_dates_and_claims_are_filtered():
    from app.services.conversation import _UNVERIFIED_CLAIM, _invented_date

    facts = "Order ORD-84102 placed 2026-09-14, shipment expected 2026-09-28"
    assert _invented_date("It should reach you by the 27th.", facts)
    assert not _invented_date("It should reach you on 28 September.", facts)
    assert _UNVERIFIED_CLAIM.search("This has already been reported by others.")


def test_known_caller_saying_ordered_and_charged_twice_goes_to_billing_without_an_order_id(client):
    """Regression: "I ordered earbuds on Sunday and got charged twice" was routed to the order desk and answered with tracking."""
    from tests.test_flows import _open

    client.post("/api/demo/reset")  # earlier tests may already have refunded the duplicate charge
    ws, c, tid = _open(client, "CUS-20481")
    try:
        r1 = _said(_turn(c, "I am honestly a bit stressed, I ordered earbuds on Sunday and I think I got charged twice for them"))
        t = client.get(f"/api/tickets/{tid}").json()
        assert t["assigned_agent"] == "Billing" and t["order_id"] == "ORD-83921"
        assert "2,499" in r1 and "tracking" not in r1.lower() and "pune" not in r1.lower()
        _turn(c, "yes that's the one, can you tell me exactly what the two charges were")
        r3 = _said(_turn(c, "ok please refund the extra one"))
        t = client.get(f"/api/tickets/{tid}").json()
        assert t["status"] == "WAITING_FOR_HUMAN" and any(a["status"] == "PENDING" for a in t["pending_actions"])
        assert "nothing is refunded yet" in r3.lower() or "approv" in r3.lower()
    finally:
        ws.__exit__(None, None, None)


def test_a_sentence_that_stops_on_a_hanging_word_waits_for_the_rest():
    from app.services.conversation import _incomplete

    assert _incomplete("I don't have it in front of me but")
    assert _incomplete("my registered email is, umm")
    assert not _incomplete("yes that's the one")
    assert not _incomplete("ok please refund the extra one")
