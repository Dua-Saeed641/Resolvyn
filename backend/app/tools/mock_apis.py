"""Simulated enterprise services — project.md §38, §87.

These stand in for Customer / Order / Payment / Refund / Shipping /
Account APIs. They must never be presented in the UI as real financial
or CRM integrations (project.md §86). Responses must stay internally
consistent with data/seed_data.py (project.md §70) — e.g. a refund
created for ORD-83921 must keep the same RFD-* id everywhere it's shown.
"""

from data.seed_data import CUSTOMERS, TICKETS


def get_customer(customer_id: str) -> dict | None:
    return next((c for c in CUSTOMERS if c["customer_id"] == customer_id), None)


def get_order(order_id: str) -> dict | None:
    ticket = next((t for t in TICKETS if t.get("order_id") == order_id), None)
    if ticket is None:
        return None
    return {"order_id": order_id, "customer_id": ticket["customer_id"]}


def get_payment_transactions(order_id: str) -> list[dict]:
    raise NotImplementedError


def check_refund_policy(order_id: str) -> dict:
    raise NotImplementedError


def issue_refund(order_id: str, amount: float) -> dict:
    raise NotImplementedError


def verify_refund(refund_id: str) -> dict:
    raise NotImplementedError
