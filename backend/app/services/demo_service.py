"""Demo Mode orchestration (project.md §46-48; docs/architecture.md §2.7).

Drives the scripted PH-1042 trace end to end — classify, route, retrieve,
propose, approve, execute, verify, resolve — emitting one agent_event per
step so the frontend can replay it as a real-time activity stream.

Not yet implemented: wire this to agents/orchestrator.py + services/
ticket_service.py once the event model (models/agent_event.py) is backed
by real persistence instead of seed data.
"""

DEMO_SCRIPT = [
    {"t": 0, "event": "Ticket created", "detail": "PH-1042 entered queue"},
    {"t": 2, "event": "Intent classified", "detail": "Duplicate Payment"},
    {"t": 4, "event": "Agent assigned", "detail": "Billing Agent"},
    {"t": 6, "event": "Customer retrieved", "detail": "CUS-20481"},
    {"t": 8, "event": "Payment records retrieved", "detail": "ORD-83921"},
    {"t": 10, "event": "Policy retrieved", "detail": "Billing Refund Policy"},
    {"t": 12, "event": "Duplicate transaction detected", "detail": None},
    {"t": 14, "event": "Human approval requested", "detail": "Refund ₹2,499"},
    {"t": 17, "event": "Human approved", "detail": "Operator 01"},
    {"t": 19, "event": "Refund executed", "detail": "RFD-28192"},
    {"t": 21, "event": "Action verified", "detail": None},
    {"t": 23, "event": "Ticket resolved", "detail": "PH-1042"},
]


def run_demo() -> list[dict]:
    """Return the full scripted event sequence for the frontend to replay."""
    return DEMO_SCRIPT


def reset_demo() -> None:
    """Reset PH-1042 and its dependent state back to its pre-demo status.

    No-op until ticket persistence exists — see ticket_service.py.
    """
    raise NotImplementedError("Wire up once ticket persistence replaces seed data.")
