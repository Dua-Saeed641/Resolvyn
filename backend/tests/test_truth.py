"""The truth guard's rules (services/truth.py)."""

import pytest

from app.services import truth

FACTS = ["Order ORD-84102: Aluminium Laptop Stand, ₹1,899, placed 2026-09-14, status Shipped",
         "Shipment SHP-5477 with Ecom Express: Delayed, at Nagpur hub, expected 2026-09-28"]
EVIDENCE = truth.evidence_text(FACTS, ["Refunds take 3 to 5 working days."], [], "where is my order")


@pytest.mark.parametrize("sentence", [
    "Your Laptop Stand, order ORD-84102, is delayed at the Nagpur hub.",
    "It should reach you on 28 September.",
    "That's ₹1,899 in total.",
    "A refund takes 3 to 5 working days.",
    "Riya here, hang on a second.",
])
def test_grounded_sentences_pass(sentence):
    assert truth.violation(sentence, EVIDENCE, FACTS) is None, sentence


@pytest.mark.parametrize("sentence,why", [
    ("It'll be with you by the 27th.", "date"),
    ("It will arrive on 30 September.", "date"),
    ("That comes to ₹2,499.", "amount"),
    ("Your order ORD-99999 is on the way.", "ID"),
    ("It should take about 2 days.", "time frame"),
    ("This has already been reported by other customers.", "claim"),
    ("I've refunded the duplicate charge.", "done"),
    ("Your account is unlocked now.", "done"),
])
def test_ungrounded_specifics_are_caught(sentence, why):
    assert why in (truth.violation(sentence, EVIDENCE, FACTS) or ""), sentence


def test_a_completed_action_is_allowed_only_when_a_tool_verified_it():
    verified = ["Refund RFD-28192 of ₹2,499 executed and VERIFIED (status COMPLETED)"]
    ev = truth.evidence_text(verified)
    assert truth.violation("Done, I've refunded ₹2,499, reference RFD-28192.", ev, verified) is None
    waiting = ["Refund of ₹2,499 for ORD-83921 is waiting for human approval (not executed)"]
    assert truth.violation("Done, I've refunded ₹2,499.", truth.evidence_text(waiting), waiting)


def test_what_the_caller_said_is_fair_evidence():
    ev = truth.evidence_text([], [], [], "I paid 2,499 rupees on the 20th")
    assert truth.violation("So that's ₹2,499 on the 20th.", ev, []) is None


def test_the_guard_costs_microseconds():
    import time
    t = time.perf_counter()
    for _ in range(2000):
        truth.violation("It should reach you on 28 September, ₹1,899, order ORD-84102, about 3 to 5 working days.", EVIDENCE, FACTS)
    assert (time.perf_counter() - t) / 2000 < 0.0005


def test_an_error_code_seen_nowhere_in_memory_is_unfamiliar():
    from app.decision_engine.decision_engine import unfamiliar_code as u

    assert u("my kettle beeps and shows error E-12", ["Smart kettle not heating: unplug it"]) == "E-12"
    assert u("the case shows B-9", ["earbuds case"]) == "B-9"
    assert u("error P-77 on headphones", ["Bug: purple light P-77. Human suggestion: hold the power button"]) is None
    assert u("error E12", ["E-12 fix"]) is None  # spelling differences do not matter
    assert u("where is order ORD-83921, USB-C cable", []) is None  # IDs and product words are not fault codes
