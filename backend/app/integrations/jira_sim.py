"""Simulated Jira / Zoho sync (docs/architecture.md §2.4).

The real system keeps ticket status "constantly monitored in Atlassian / Zoho,
autonomously". No Jira instance is connected in this prototype: this module
mirrors ticket status into a simulated issue key + workflow status and runs the
autonomous monitor loop. The UI labels it "Simulation" (docs/claude.md).
"""

import asyncio

from sqlmodel import Session, select

from app.database import engine
from app.models import Ticket
from app.services import ticket_service as tickets
from app.utils import as_utc, utcnow

WORKFLOW = {
    "NEW": "To Do",
    "ANALYZING": "To Do",
    "ROUTING": "To Do",
    "ACTIVE": "In Progress",
    "WAITING_FOR_HUMAN": "Waiting for support",
    "VERIFYING": "In Review",
    "RESOLVED": "Done",
    "FAILED": "Blocked",
}
SLA_SECONDS = 180
_warned: set[str] = set()


def key_for(ticket_id: str) -> str:
    return f"RSV-{ticket_id.split('-')[1]}"


def sync(ticket_id: str, *, reason: str = "monitor") -> None:
    t = tickets.get(ticket_id)
    if not t:
        return
    status = WORKFLOW.get(t.status, "To Do")
    if t.jira_key == key_for(ticket_id) and t.jira_status == status:
        return
    first = t.jira_key is None
    tickets.update(ticket_id, jira_key=key_for(ticket_id), jira_status=status)
    tickets.add_event(
        ticket_id, "Jira (simulated)", "JIRA_SYNCED",
        f"{'Issue ' + key_for(ticket_id) + ' created' if first else key_for(ticket_id) + ' moved'} → {status} ({reason})",
        status="COMPLETED",
    )


async def monitor(interval: float = 8.0) -> None:
    """Autonomous monitoring loop: keeps Jira in step and raises SLA warnings."""
    while True:
        await asyncio.sleep(interval)
        try:
            with Session(engine) as s:
                open_tickets = s.exec(select(Ticket).where(Ticket.status != "RESOLVED")).all()
            for t in open_tickets:
                if t.jira_key:
                    sync(t.ticket_id)
                if t.status == "WAITING_FOR_HUMAN" and t.ticket_id not in _warned:
                    waited = (utcnow() - as_utc(t.updated_at)).total_seconds()
                    if waited > SLA_SECONDS:
                        _warned.add(t.ticket_id)
                        tickets.add_event(t.ticket_id, "Jira (simulated)", "SLA_WARNING",
                                          f"Waiting for a human for {int(waited)}s — SLA at risk", status="WAITING")
        except Exception as e:  # noqa: BLE001
            print(f"[jira_sim] monitor error: {e}", flush=True)
