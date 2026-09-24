"""Ticket list/detail — docs/architecture.md §2.4 (ticket lifecycle)."""

from fastapi import APIRouter, HTTPException

from app.services import ticket_service

router = APIRouter()


@router.get("")
def list_tickets():
    return ticket_service.list_tickets()


@router.get("/{ticket_id}")
def get_ticket(ticket_id: str):
    ticket = ticket_service.get_ticket(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket
