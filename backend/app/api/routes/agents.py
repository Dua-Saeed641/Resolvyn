"""Department agents and their live state (docs/architecture.md §2.3, project.md §19-21)."""

from fastapi import APIRouter

from app.agents import orchestrator
from app.services import ticket_service

router = APIRouter()


@router.get("")
def list_agents():
    return orchestrator.list_agents()


@router.get("/{name}/tickets")
def agent_tickets(name: str):
    return ticket_service.list_tickets(agent=name)
