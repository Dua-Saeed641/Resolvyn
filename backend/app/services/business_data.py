"""The business database: seeding, lookups and bulk import of orders, payments, shipments and customers.

Everything the department agents *say* about an order comes from here, through the tool layer. Lookups are forgiving
because callers give IDs the way people say them ("3508", "order 83921", "O R D 83921").
"""

import csv
import io
import json
import re

from sqlmodel import Session, select

from app.database import engine
from app.models import AccountState, Customer, Order, Payment, Shipment
from data.seed_data import ACCOUNTS, CUSTOMERS, LEGACY_CUSTOMER_IDS, ORDERS, PAYMENTS, SHIPMENTS


def _digits(s: str) -> str:
    return re.sub(r"\D", "", s or "")


def order_dict(o: Order) -> dict:
    return {"order_id": o.order_id, "customer_id": o.customer_id, "item": o.item, "amount": o.amount,
            "placed": o.placed, "status": o.status, "shipment_id": o.shipment_id}


def seed() -> dict:
    """Load the demo business data; idempotent (never overwrites what already exists)."""
    n = {"orders": 0, "payments": 0, "shipments": 0, "accounts": 0}
    with Session(engine) as s:
        for o in ORDERS.values():
            row = s.get(Order, o["order_id"])
            if not row:
                s.add(Order(**o))
                n["orders"] += 1
            elif row.customer_id != o["customer_id"]:  # owner changed when the demo went down to two customers
                row.customer_id = o["customer_id"]
                s.add(row)
        for oid, plist in PAYMENTS.items():
            for p in plist:
                row = s.get(Payment, p["transaction_id"])
                if not row:
                    s.add(Payment(order_id=oid, **p))
                    n["payments"] += 1
                elif row.method != p["method"]:
                    row.method = p["method"]
                    s.add(row)
        for sh in SHIPMENTS.values():
            if not s.get(Shipment, sh["shipment_id"]):
                s.add(Shipment(**sh))
                n["shipments"] += 1
        for cid, a in ACCOUNTS.items():
            if not s.get(AccountState, cid):
                s.add(AccountState(customer_id=cid, **a))
                n["accounts"] += 1
        for legacy in LEGACY_CUSTOMER_IDS:
            gone = s.get(AccountState, legacy)
            if gone:
                s.delete(gone)
        s.commit()
    return n


def reset_demo() -> None:
    """Put the demo records back the way the seed defines them (used by RESET DEMO)."""
    with Session(engine) as s:
        for o in ORDERS.values():
            row = s.get(Order, o["order_id"])
            if row:
                row.status = o["status"]
                s.add(row)
        for cid, a in ACCOUNTS.items():
            row = s.get(AccountState, cid)
            if row:
                row.status, row.failed_logins, row.locked_reason = a["status"], a["failed_logins"], a.get("locked_reason")
                s.add(row)
        s.commit()


# ── lookups ──────────────────────────────────────────────────────────────────


def lookup_order(ref: str) -> dict:
    """Find an order from whatever the caller said. Returns {"found", "match", "order"} or {"found": False, "candidates"}.

    exact      ORD-83921            partial   "83921" / "3921" (unique tail match)      ambiguous  several orders match
    """
    ref = (ref or "").strip().upper()
    d = _digits(ref)
    with Session(engine) as s:
        if ref:
            o = s.get(Order, ref) or (s.get(Order, f"ORD-{d}") if d else None)
            if o:
                return {"found": True, "match": "exact", "order": order_dict(o)}
        if len(d) >= 3:
            hits = [o for o in s.exec(select(Order)).all() if _digits(o.order_id).endswith(d)]
            if len(hits) == 1:
                return {"found": True, "match": "partial", "order": order_dict(hits[0])}
            if len(hits) > 1:
                return {"found": False, "match": "ambiguous", "candidates": [order_dict(o) for o in hits[:5]]}
    return {"found": False, "match": "none", "candidates": []}


def orders_for_customer(customer_id: str) -> list[dict]:
    with Session(engine) as s:
        rows = s.exec(select(Order).where(Order.customer_id == customer_id)).all()
    return [order_dict(o) for o in sorted(rows, key=lambda o: o.placed, reverse=True)]


def customers_matching(name: str | None = None, email: str | None = None, phone_last4: str | None = None) -> list[dict]:
    with Session(engine) as s:
        rows = s.exec(select(Customer)).all()
    out = []
    for c in rows:
        if email and (c.email or "").lower() == email.lower():
            out.append(c)
        elif phone_last4 and c.phone_last4 == phone_last4:
            out.append(c)
        elif name and not email and not phone_last4:
            n = name.strip().lower()
            if c.name.lower() == n or c.name.lower().split()[0] == n.split()[0]:
                out.append(c)
    return [c.model_dump() for c in out]


# ── bulk import (own business data) ──────────────────────────────────────────

_ORDER_COLS = {"order_id", "customer_id", "item", "amount", "placed", "status", "shipment_id"}
_PAY_COLS = {"transaction_id", "order_id", "amount", "status", "method", "timestamp"}
_SHIP_COLS = {"shipment_id", "carrier", "status", "location", "eta", "delayed", "delay_reason"}
_CUST_COLS = {"customer_id", "name", "email", "phone_last4", "plan", "account_age_years"}


def _rows(filename: str, raw: bytes) -> list[dict]:
    text = raw.decode("utf-8-sig", errors="replace")
    if filename.lower().endswith(".json"):
        data = json.loads(text)
        return data if isinstance(data, list) else [data]
    return [{(k or "").strip().lower(): (v or "").strip() for k, v in r.items()} for r in csv.DictReader(io.StringIO(text))]


def _kind(cols: set[str], hint: str | None) -> str | None:
    if hint in ("orders", "payments", "shipments", "customers"):
        return hint
    if {"order_id", "item"} <= cols:
        return "orders"
    if {"transaction_id", "order_id"} <= cols:
        return "payments"
    if {"shipment_id", "carrier"} <= cols:
        return "shipments"
    if {"customer_id", "name"} <= cols:
        return "customers"
    return None


def import_records(filename: str, raw: bytes, kind: str | None = None) -> dict:
    """Upsert orders / payments / shipments / customers from a CSV or JSON file. The kind is detected from the columns."""
    rows = _rows(filename, raw)
    if not rows:
        return {"kind": None, "imported": 0}
    kind = _kind({k.lower() for k in rows[0]}, kind)
    if not kind:
        raise ValueError("Columns not recognised. Orders need order_id,item; payments transaction_id,order_id; "
                         "shipments shipment_id,carrier; customers customer_id,name.")
    model, cols = {"orders": (Order, _ORDER_COLS), "payments": (Payment, _PAY_COLS),
                   "shipments": (Shipment, _SHIP_COLS), "customers": (Customer, _CUST_COLS)}[kind]
    pk = {"orders": "order_id", "payments": "transaction_id", "shipments": "shipment_id", "customers": "customer_id"}[kind]
    count = 0
    with Session(engine) as s:
        for r in rows:
            data = {k: v for k, v in r.items() if k in cols and v not in ("", None)}
            if not data.get(pk):
                continue
            data[pk] = str(data[pk]).upper() if kind != "customers" else str(data[pk])
            if "order_id" in data:
                data["order_id"] = str(data["order_id"]).upper()
            if "amount" in data:
                data["amount"] = int(float(str(data["amount"]).replace(",", "").replace("₹", "")))
            if "account_age_years" in data:
                data["account_age_years"] = int(float(data["account_age_years"]))
            if "delayed" in data:
                data["delayed"] = str(data["delayed"]).lower() in ("1", "true", "yes", "y")
            row = s.get(model, data[pk])
            if row:
                for k, v in data.items():
                    setattr(row, k, v)
            else:
                row = model(**data)
            s.add(row)
            if kind == "customers":
                s.merge(AccountState(customer_id=data["customer_id"]))
            count += 1
        s.commit()
    return {"kind": kind, "imported": count}


def snapshot() -> dict:
    """Everything, for the team console."""
    with Session(engine) as s:
        return {
            "orders": [order_dict(o) for o in s.exec(select(Order)).all()],
            "payments": [p.model_dump() for p in s.exec(select(Payment)).all()],
            "shipments": [x.model_dump() for x in s.exec(select(Shipment)).all()],
            "accounts": [a.model_dump() for a in s.exec(select(AccountState)).all()],
            "customers": [c.model_dump() for c in s.exec(select(Customer)).all()],
        }
