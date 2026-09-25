"""Deterministic building blocks: perception, Jev rules, speech text, retrieval."""

from app.judgment import jev
from app.perception.perception_service import detect_language, extract_entities
from app.voice import speech


def test_entities_from_noisy_speech():
    assert extract_entities("my order id is O R D 8 3 9 2 1")["order_id"] == "ORD-83921"
    assert extract_entities("order ORD-83921 please")["order_id"] == "ORD-83921"
    assert extract_entities("it is lovekesh dot anand at example dot com")["email"] == "lovekesh.anand@example.com"
    assert extract_entities("the last four digits of my registered phone are 3390")["phone_last4"] == "3390"
    ent = extract_entities("my name is Lovekesh Anand and the order ID is ORD-83921")
    assert ent["name"] == "Lovekesh Anand" and ent["order_id"] == "ORD-83921"
    assert "name" not in extract_entities("I am so frustrated")


def test_language_detection():
    assert detect_language("I want a refund") == "en"
    assert detect_language("mera order abhi tak nahi aaya, kya aap check kar sakte hain") == "hi"
    assert detect_language("मेरे ऑर्डर में दो बार पैसे कट गए हैं") == "hi"


def test_jev_routing_and_dialogue_acts():
    cases = {
        "I was charged twice for the same order": ("Duplicate Payment", "Billing"),
        "my account is locked and I can't log in": ("Account Access", "Account"),
        "where my order ORD-84155 is": ("Shipping Delay", "Order"),
        "my headphones are flashing purple with error code P-77": ("Technical Issue", "Technical"),
    }
    for text, (intent, dept) in cases.items():
        j = jev.rules_judge(text)
        assert (j.intent, j.department) == (intent, dept), text
    assert jev.rules_judge("yes please go ahead").yes
    assert jev.rules_judge("no, leave it").no
    assert jev.rules_judge("it worked, the light is white now").yes
    assert jev.rules_judge("still not working").no
    assert jev.rules_judge("I want to speak to a manager").wants_human
    assert jev.rules_judge("this is ridiculous, worst service").sentiment in ("Frustrated", "Angry")


def test_addressee_detects_side_talk():
    assert jev.addressee("Mom, can you turn the TV down a little? I'm on the phone.", expecting_answer=False)[0] == "other"
    assert jev.addressee("hey mom one second", expecting_answer=True)[0] == "other"
    assert jev.addressee("My order ID is ORD-83921", expecting_answer=True)[0] == "agent"
    assert jev.addressee("yes please", expecting_answer=True)[0] == "agent"
    assert jev.addressee("I was charged twice for my order", expecting_answer=False)[0] == "agent"


def test_sentence_streamer_never_splits_numbers():
    st = speech.SentenceStreamer()
    out = []
    for piece in ["Your refund of ₹2,499 is done", " and confirmed. The reference is RFD-28192.", " Anything else?"]:
        out += st.feed(piece)
    tail = st.flush()
    if tail:
        out.append(tail)
    joined = " ".join(out)
    assert "₹2,499" in joined
    assert not any(s.endswith("₹2,") for s in out)
    assert len(out) >= 2


def test_spoken_text_normalisation():
    spoken = speech.to_spoken("Refund ₹2,499 for ORD-83921 is **done** 🙂")
    assert "2,499 rupees" in spoken
    assert "O R D" in spoken and "8 3 9 2 1" in spoken
    assert "*" not in spoken and "🙂" not in spoken


def test_retrieval_separates_known_from_unknown(client):  # client fixture seeds the DB
    from app.memory.memory_engine import memory

    known = memory.retrieve("I was charged twice for the same order and want a refund", "Billing")
    assert known.best_common >= 0.5 and known.top_hits(1)[0].kind in ("sop", "business_logic", "past_query")
    unknown = memory.retrieve("my smart fridge makes a grinding noise and leaks coolant", "Technical")
    assert unknown.best < 0.28


def test_ingest_makes_new_knowledge_retrievable(client):
    from app.memory.memory_engine import memory

    before = memory.retrieve("gift card corporate bulk order discount", "Other").best_common
    r = client.post("/api/knowledge/ingest-text", json={
        "title": "Corporate gift cards",
        "text": "# Corporate gift cards\nCorporate customers can buy gift cards in bulk. Bulk gift card orders above 50 cards get a 10 percent discount.\n",
        "kind": "sop", "department": "Other",
    })
    assert r.status_code == 200 and r.json()["chunks"] >= 1
    after = memory.retrieve("gift card corporate bulk order discount", "Other").best_common
    assert after > before and after >= 0.5
    rulebook = client.get("/api/knowledge/rulebook/by-department").json()
    assert set(rulebook) == {"Technical", "Billing", "Account", "Order", "Other"}
