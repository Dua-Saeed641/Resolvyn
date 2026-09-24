"""Simulated enterprise services — project.md §38, §87.

These stand in for Customer / Order / Payment / Refund / Shipping / Account
APIs. They must never be presented in the UI as real financial or CRM
integrations (project.md §86). Responses stay internally consistent with
data/seed_data.py (project.md §70) — a refund created for ORD-83921 keeps the
same RFD-* id everywhere it is shown.
"""

from sqlmodel import Session, select

from app.database import engine
from app.models import Customer, Refund
from app.utils import iso
from data.seed_data import ACCOUNTS, ORDERS, PAYMENTS, SHIPMENTS

REFUND_ID_BASE = 28192
DUPLICATE_WINDOW_SECONDS = 600


class ApiUnavailable(RuntimeError):
    """The simulated upstream service did not respond (project.md §88)."""


# One-shot failure injection so the retry path can be demonstrated on demand.
_FAIL_ONCE: set[str] = set()


def fail_next(tool_name: str) -> None:
    _FAIL_ONCE.add(tool_name)


def _maybe_fail(tool_name: str) -> None:
    if tool_name in _FAIL_ONCE:
        _FAIL_ONCE.discard(tool_name)
        raise ApiUnavailable(f"{tool_name}: upstream service did not return a valid response")


# ── Customer / account ───────────────────────────────────────────────────────


def get_customer(customer_id: str) -> dict | None:
    _maybe_fail("get_customer")
    with Session(engine) as s:
        c = s.get(Customer, customer_id)
        return c.model_dump() if c else None


def find_customer(name: str | None = None, email: str | None = None) -> dict | None:
    _maybe_fail("find_customer")
    with Session(engine) as s:
        rows = s.exec(select(Customer)).all()
    for c in rows:
        if email and c.email and c.email.lower() == email.lower():
            return c.model_dump()
    if name:
        n = name.strip().lower()
        for c in rows:
            if c.name.lower() == n or c.name.lower().split()[0] == n:
                return c.model_dump()
    return None


def verify_identity(customer_id: str, email: str | None = None, phone_last4: str | None = None) -> dict:
    _maybe_fail("verify_identity")
    c = get_customer(customer_id)
    if not c:
        return {"verified": False, "reason": "customer not found"}
    ok_email = bool(email) and (c.get("email") or "").lower() == email.lower()
    ok_phone = bool(phone_last4) and c.get("phone_last4") == phone_last4
    return {"verified": ok_email or ok_phone, "matched": "email" if ok_email else "phone" if ok_phone else None}


def get_account_status(customer_id: str) -> dict:
    _maybe_fail("get_account_status")
    acc = ACCOUNTS.get(customer_id)
    if not acc:
        return {"customer_id": customer_id, "status": "UNKNOWN"}
    return {"customer_id": customer_id, **acc}


def unlock_account(customer_id: str) -> dict:
    _maybe_fail("unlock_account")
    acc = ACCOUNTS.get(customer_id)
    if not acc:
        return {"ok": False, "reason": "account not found"}
    acc.update({"status": "ACTIVE", "failed_logins": 0})
    acc.pop("locked_reason", None)
    return {"ok": True, "status": "ACTIVE"}


def send_reset_link(customer_id: str) -> dict:
    _maybe_fail("send_reset_link")
    c = get_customer(customer_id)
    if not c:
        return {"ok": False, "reason": "customer not found"}
    email = c["email"]
    masked = email[0] + "***" + email[email.index("@"):]
    return {"ok": True, "sent_to": masked, "expires_in_minutes": 30}


# ── Orders / shipping ────────────────────────────────────────────────────────


def get_order(order_id: str) -> dict | None:
    _maybe_fail("get_order")
    o = ORDERS.get(order_id.upper())
    return dict(o) if o else None


def get_shipment(shipment_id: str) -> dict | None:
    _maybe_fail("get_shipment")
    sh = SHIPMENTS.get(shipment_id)
    return dict(sh) if sh else None


def cancel_order(order_id: str) -> dict:
    _maybe_fail("cancel_order")
    o = ORDERS.get(order_id.upper())
    if not o:
        return {"ok": False, "reason": "order not found"}
    if o["status"] in ("Shipped", "Delivered"):
        return {"ok": False, "reason": f"order is already {o['status'].lower()}"}
    o["status"] = "Cancelled"
    return {"ok": True, "status": "Cancelled"}


# ── Payments / refunds ───────────────────────────────────────────────────────


def get_payment_transactions(order_id: str) -> list[dict]:
    _maybe_fail("get_payment_transactions")
    return [dict(p) for p in PAYMENTS.get(order_id.upper(), [])]


def _refunded_transactions(order_id: str) -> set[str]:
    with Session(engine) as s:
        rows = s.exec(select(Refund).where(Refund.order_id == order_id)).all()
    return {r.transaction_id for r in rows if r.status != "FAILED"}


def detect_duplicate(order_id: str) -> dict:
    """Two successful charges for the same order/method within the window."""
    txns = [t for t in get_payment_transactions(order_id) if t["status"] == "SUCCESS"]
    already = _refunded_transactions(order_id)
    for i, a in enumerate(txns):
        for b in txns[i + 1:]:
            if a["amount"] == b["amount"] and a["method"] == b["method"]:
                dup = b if b["transaction_id"] not in already else None
                return {
                    "duplicate": True,
                    "original": a,
                    "duplicate_txn": b,
                    "already_refunded": dup is None,
                    "refundable": dup,
                }
    return {"duplicate": False}


def check_refund_policy(order_id: str) -> dict:
    """Policy verdict for refunding the duplicate charge on this order."""
    _maybe_fail("check_refund_policy")
    order = get_order(order_id)
    if not order:
        return {"eligible": False, "reason": "order not found"}
    dup = detect_duplicate(order_id)
    if dup["duplicate"] and dup["refundable"]:
        t = dup["refundable"]
        return {
            "eligible": True,
            "reason": "Duplicate successful charge for the same order",
            "policy": "Billing Refund Policy §2: duplicate charges are always refundable",
            "amount": t["amount"],
            "transaction_id": t["transaction_id"],
        }
    if dup["duplicate"] and dup["already_refunded"]:
        return {"eligible": False, "reason": "The duplicate charge has already been refunded"}
    return {"eligible": False, "reason": "No duplicate charge found on this order"}


def issue_refund(order_id: str, transaction_id: str, amount: int, for_ticket: str | None = None) -> dict:
    _maybe_fail("issue_refund")
    with Session(engine) as s:
        existing = s.exec(
            select(Refund).where(Refund.order_id == order_id, Refund.transaction_id == transaction_id)
        ).first()
        if existing and existing.status != "FAILED":
            return {"ok": True, "refund_id": existing.refund_id, "status": existing.status, "idempotent": True}
        count = len(s.exec(select(Refund)).all())
        refund = Refund(
            refund_id=f"RFD-{REFUND_ID_BASE + count}",
            order_id=order_id,
            transaction_id=transaction_id,
            amount=amount,
            status="PROCESSING",
            ticket_id=for_ticket,
        )
        s.add(refund)
        s.commit()
        return {"ok": True, "refund_id": refund.refund_id, "status": refund.status}


def refunds_for_order(order_id: str) -> list[dict]:
    _maybe_fail("refunds_for_order")
    with Session(engine) as s:
        rows = s.exec(select(Refund).where(Refund.order_id == order_id.upper())).all()
    return [{"refund_id": r.refund_id, "amount": r.amount, "status": r.status,
             "transaction_id": r.transaction_id, "created_at": iso(r.created_at)} for r in rows]


def verify_refund(refund_id: str) -> dict:
    """Reads the refund back from the refund service — the only thing allowed
    to make Resolvyn say a refund succeeded (project.md §63)."""
    _maybe_fail("verify_refund")
    with Session(engine) as s:
        r = s.get(Refund, refund_id)
        if not r:
            return {"verified": False, "reason": "refund not found"}
        if r.status == "PROCESSING":
            r.status = "COMPLETED"  # the simulated gateway settles on first read-back
            s.add(r)
            s.commit()
        return {
            "verified": r.status == "COMPLETED",
            "refund_id": r.refund_id,
            "status": r.status,
            "amount": r.amount,
            "eta": "3 to 5 working days to your original payment method",
            "created_at": iso(r.created_at),
        }


def reset_state() -> None:
    """Reset mutable simulated state (used by RESET DEMO)."""
    with Session(engine) as s:
        for r in s.exec(select(Refund)).all():
            s.delete(r)
        s.commit()
    ACCOUNTS["CUS-20517"].update({"status": "LOCKED", "failed_logins": 5,
                                  "locked_reason": "Too many failed logins"})
    ORDERS["ORD-84155"]["status"] = "Processing"
    _FAIL_ONCE.clear()
