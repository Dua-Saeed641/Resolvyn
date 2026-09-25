"""Runs simulated enterprise API calls and records their real state.

Every call is persisted as a ToolCall (NOT_STARTED → WAITING → COMPLETED /
FAILED — docs/claude.md) and pushed to the team dashboard. The AI may only
claim what a completed call returned. One automatic retry demonstrates the
failure path from project.md §88 ("Payment API unavailable → retrying…").
"""

import asyncio
import inspect

from sqlmodel import Session

from app.database import engine
from app.models import ToolCall
from app.services import ticket_service as tickets
from app.services.realtime import hub
from app.tools import mock_apis
from app.utils import jdump, utcnow

REGISTRY = {
    "find_customer": mock_apis.find_customer,
    "get_customer": mock_apis.get_customer,
    "verify_identity": mock_apis.verify_identity,
    "get_account_status": mock_apis.get_account_status,
    "unlock_account": mock_apis.unlock_account,
    "send_reset_link": mock_apis.send_reset_link,
    "get_order": mock_apis.get_order,
    "lookup_order": mock_apis.lookup_order,
    "orders_for_customer": mock_apis.orders_for_customer,
    "get_shipment": mock_apis.get_shipment,
    "cancel_order": mock_apis.cancel_order,
    "get_payment_transactions": mock_apis.get_payment_transactions,
    "check_refund_policy": mock_apis.check_refund_policy,
    "issue_refund": mock_apis.issue_refund,
    "verify_refund": mock_apis.verify_refund,
    "refunds_for_order": mock_apis.refunds_for_order,
}

# Simulated network latency so the dashboard shows WAITING → COMPLETED honestly.
LATENCY = 0.35


def _tool_payload(row: ToolCall) -> dict:
    return tickets.tool_dict(row)


async def call(ticket_id: str, name: str, agent: str, /, **kwargs):
    """Execute a tool. Returns (ok, result). Never raises."""
    fn = REGISTRY[name]
    with Session(engine, expire_on_commit=False) as s:
        row = ToolCall(ticket_id=ticket_id, tool_name=name, status="WAITING", request=jdump(kwargs))
        s.add(row)
        s.commit()
    hub.to_ops({"type": "tool_call", "tool_call": _tool_payload(row)})
    tickets.add_event(ticket_id, agent, "TOOL_CALLED", f"{name}({', '.join(f'{k}={v}' for k, v in kwargs.items())})",
                      status="WAITING")

    result, ok, error = None, False, None
    for attempt in (1, 2):
        await asyncio.sleep(LATENCY)
        try:
            result = fn(**kwargs)
            if inspect.isawaitable(result):
                result = await result
            ok = True
            break
        except mock_apis.ApiUnavailable as e:
            error = str(e)
            if attempt == 1:
                _record(row, "FAILED", {"error": error, "retrying": True})
                tickets.add_event(ticket_id, agent, "TOOL_CALLED", f"{name} failed — retrying verification…",
                                  status="FAILED")
                continue
        except Exception as e:  # noqa: BLE001
            error = f"{type(e).__name__}: {e}"
            break

    if ok:
        _record(row, "COMPLETED", result)
        tickets.add_event(ticket_id, agent, "TOOL_CALLED", f"{name} completed", status="COMPLETED",
                          meta={"tool": name})
    else:
        _record(row, "FAILED", {"error": error})
        tickets.add_event(ticket_id, agent, "TOOL_CALLED", f"{name} failed: {error}", status="FAILED")
    return ok, (result if ok else {"error": error})


def _record(row: ToolCall, status: str, response) -> None:
    with Session(engine, expire_on_commit=False) as s:
        r = s.get(ToolCall, row.tool_call_id)
        r.status = status
        r.response = jdump(response)
        r.timestamp = utcnow()
        s.add(r)
        s.commit()
        row.status, row.response = r.status, r.response
    hub.to_ops({"type": "tool_call", "tool_call": _tool_payload(r)})
