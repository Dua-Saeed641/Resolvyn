"""System-wide event stream (project.md §14, §37)."""

from fastapi import APIRouter

from app.services import ticket_service

router = APIRouter()


@router.get("")
def recent(limit: int = 150):
    return ticket_service.recent_events(min(limit, 500))
