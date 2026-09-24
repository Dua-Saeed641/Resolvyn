"""Context & Memory Engine — docs/architecture.md §1 layer 3, §2.6.

Two logical stores, each split vector / knowledge-graph:
  - common/past-query memory  (Business logic, Pure SOPs, Product DB)
  - first-time-bug memory     (issues with no company precedent)

Also holds short-term (current conversation) and episodic (past ticket)
memory per customer, surfaced as "Relevant customer history found"
(project.md §61).

Not yet implemented: prototype-scale placeholder only (project.md §3.2
excludes production-scale vector databases from v1).
"""

from typing import TypedDict


class PriorInteraction(TypedDict):
    ticket_id: str
    summary: str
    resolution: str


def get_customer_history(customer_id: str) -> list[PriorInteraction]:
    raise NotImplementedError("Wire up to data/seed_data.py TICKETS filtered by customer_id.")


def is_first_time_bug(query: str) -> bool:
    """True if `query` has no match in the common/past-query store.

    Drives the "A FIRST TIME BUG HAS BEEN REPORTED" path
    (docs/architecture.md §2.6).
    """
    raise NotImplementedError
