"""Customer profiles + history (project.md §17, §69)."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from app.database import engine
from app.models import Customer
from app.services import analytics_service, ticket_service

router = APIRouter()


@router.get("")
def list_customers():
    return analytics_service.customers()


@router.get("/{customer_id}/portal-tickets")
def portal_tickets(customer_id: str):
    """Customer-safe view of a caller's own tickets (no confidence, no internal summary)."""
    rows = ticket_service.tickets_for_customer(customer_id)
    return [ticket_service.customer_view(r["ticket_id"]) for r in rows]


class EmailIn(BaseModel):
    email: str


@router.patch("/{customer_id}/email")
def set_email(customer_id: str, body: EmailIn):
    """Where this customer's summaries and replies are emailed."""
    email = body.email.strip()
    if "@" not in email or " " in email:
        raise HTTPException(400, "Enter a valid email address")
    with Session(engine) as s:
        c = s.get(Customer, customer_id)
        if not c:
            raise HTTPException(404, "Customer not found")
        c.email = email
        s.add(c)
        s.commit()
        return {"customer_id": customer_id, "email": c.email}


@router.get("/{customer_id}")
def get_customer(customer_id: str):
    with Session(engine) as s:
        c = s.get(Customer, customer_id)
    if not c:
        raise HTTPException(404, "Customer not found")
    return {**c.model_dump(), "tickets": ticket_service.tickets_for_customer(customer_id)}
