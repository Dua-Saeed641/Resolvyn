"""Jev, the fast judgment layer: intent and department, sentiment, human requests, dialogue acts and side talk.

Jev runs on every caller sentence before any model, so it has to be right on its own and fast.
"""

import time

import pytest

from app.judgment import jev

ROUTING = [
    # (caller says, expected intent, expected department)
    ("I was charged twice for the same order", "Duplicate Payment", "Billing"),
    ("I ordered earbuds on Sunday and got charged twice for them", "Duplicate Payment", "Billing"),
    ("paise do baar kat gaye mere account se", "Duplicate Payment", "Billing"),
    ("where is my refund, it's been a week", "Refund Status", "Billing"),
    ("I want my money back", "Refund Request", "Billing"),
    ("the payment failed but money was deducted", "Payment Failure", "Billing"),
    ("my account is locked and I can't log in", "Account Access", "Account"),
    ("password bhool gaya, login nahi ho raha", "Account Access", "Account"),
    ("I want to change my email address", "Profile Update", "Account"),
    ("where is my order, it hasn't arrived", "Shipping Delay", "Order"),
    ("mera order abhi tak nahi aaya", "Shipping Delay", "Order"),
    ("I want to cancel my order", "Order Issue", "Order"),
    ("I received the wrong colour", "Order Issue", "Order"),
    ("I ordered something day before yesterday and wanted to check on it", "Order Issue", "Order"),
    ("my headphones won't pair over bluetooth", "Technical Issue", "Technical"),
    ("the app keeps crashing after the update", "Technical Issue", "Technical"),
    ("how do I claim warranty", "Technical Issue", "Technical"),
    ("how much is the portable speaker mini", "General Query", "Other"),
]


@pytest.mark.parametrize("text,intent,dept", ROUTING)
def test_routes_to_the_right_desk(text, intent, dept):
    j = jev.rules_judge(text)
    assert (j.intent, j.department) == (intent, dept), f"{text!r} -> {j.intent}/{j.department}"


def test_follow_up_keeps_the_topic_but_a_new_question_switches_it():
    first = jev.rules_judge("I got charged twice for my earbuds")
    for follow in ("my name is Lovekesh and the order ID is ORD-83921", "ok please refund the extra one", "how long until the money shows up"):
        assert jev.rules_judge(follow, first).department == "Billing", follow
    assert jev.rules_judge("while you are there, where is the parcel? it's been a few days", first).department == "Order"
    assert jev.rules_judge("what's the warranty on these earbuds, does water damage count?", first).department == "Technical"


@pytest.mark.parametrize("text,sentiment", [
    ("this is ridiculous, third time I'm calling", "Angry"),
    ("I'm really frustrated with this", "Frustrated"),
    ("thanks, that was really helpful", "Positive"),
    ("my order is late", "Neutral"),
])
def test_sentiment(text, sentiment):
    assert jev.rules_judge(text).sentiment == sentiment


@pytest.mark.parametrize("text,wants", [
    ("I want to speak to a manager", True),
    ("can I talk to a real person please", True),
    ("manager se baat karni hai", True),
    ("mujhe kisi insaan se baat karni hai", True),
    ("are you a real person or a bot?", False),
    ("I don't want to talk to a manager, just fix it", False),
    ("no need to escalate, it's fine", False),
])
def test_human_request(text, wants):
    assert jev.rules_judge(text).wants_human is wants, text


@pytest.mark.parametrize("text,yes,no,done", [
    ("yes please", True, False, False),
    ("haan kar do", True, False, False),
    ("no, leave it", False, True, False),
    ("that's all, thanks", False, False, True),
    ("dhanyavaad, bas itna hi", False, False, True),
    ("it still doesn't work", False, True, False),
])
def test_dialogue_acts(text, yes, no, done):
    y, n, d = jev.dialogue_act(text)
    assert (y, n, d) == (yes, no, done), text


@pytest.mark.parametrize("text,expecting,who", [
    ("Mom, can you turn the TV down?", False, "other"),
    ("one second mom", False, "other"),
    ("sorry, not you, I was talking to my brother", False, "other"),
    ("yes that's right", True, "agent"),
    ("my order ID is ORD-83921", False, "agent"),
    ("mom turn the tv down. sorry, where were we", False, "agent"),
])
def test_side_talk(text, expecting, who):
    assert jev.addressee(text, expecting_answer=expecting)[0] == who, text


def test_urgency_and_priority():
    j = jev.rules_judge("this is unacceptable, I need the refund right now", plan="Premium")
    assert j.urgency == "High" and j.priority == "CRITICAL"
    assert jev.rules_judge("I was charged twice", plan="Premium").priority == "HIGH"


def test_jev_is_fast_enough_for_live_speech():
    lines = [t for t, _, _ in ROUTING] * 20
    t0 = time.perf_counter()
    for line in lines:
        jev.rules_judge(line)
        jev.addressee(line, expecting_answer=False)
    per_line_ms = (time.perf_counter() - t0) * 1000 / len(lines)
    assert per_line_ms < 5, f"Jev took {per_line_ms:.2f} ms per sentence"


def test_jev_lab_endpoint(client):
    r = client.post("/api/jev/judge", json={"text": "I want to speak to a manager, I was charged twice"})
    d = r.json()
    assert r.status_code == 200 and d["judgment"]["wants_human"] and d["judgment"]["department"] == "Billing"
    assert d["addressee"]["who"] == "agent" and d["ms"] < 50 and d["route"] == "ESCALATED"
