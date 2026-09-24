"""Owns ticket state (docs/architecture.md §2.4, §3 mapping table).

Reads from the deterministic seed data for now. Once persistence is wired
up, this is the only module allowed to read/write the `tickets` table —
routes and other services must go through it rather than querying directly
(project.md §58, "backend should own ticket state").
"""

from data.seed_data import TICKETS


def list_tickets() -> list[dict]:
    return TICKETS


def get_ticket(ticket_id: str) -> dict | None:
    return next((t for t in TICKETS if t["ticket_id"] == ticket_id), None)
