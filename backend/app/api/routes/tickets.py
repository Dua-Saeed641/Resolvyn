"""Ticket list/detail — docs/architecture.md §2.4 (ticket lifecycle)."""

from fastapi import APIRouter, HTTPException

from app.services import ticket_service

router = APIRouter()


@router.get("")
def list_tickets(status: str | None = None, agent: str | None = None):
    return ticket_service.list_tickets(status=status, agent=agent)


@router.get("/{ticket_id}")
def get_ticket(ticket_id: str):
    ticket = ticket_service.detail(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@router.get("/{ticket_id}/customer-view")
def customer_view(ticket_id: str):
    view = ticket_service.customer_view(ticket_id)
    if view is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return view
