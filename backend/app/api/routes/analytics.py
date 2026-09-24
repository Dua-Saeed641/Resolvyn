"""Aggregate metrics — project.md §66."""

from fastapi import APIRouter

from data.seed_data import TICKETS

router = APIRouter()


@router.get("")
def get_analytics():
    resolved = sum(1 for t in TICKETS if t["status"] == "RESOLVED")
    active = sum(1 for t in TICKETS if t["status"] not in ("RESOLVED", "FAILED"))
    return {
        "tickets_today": len(TICKETS),
        "resolved": resolved,
        "active": active,
        "human_interventions": sum(1 for t in TICKETS if t["status"] == "WAITING_FOR_HUMAN"),
    }
