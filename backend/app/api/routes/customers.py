"""Customer context panel data — project.md §17, §69."""

from fastapi import APIRouter, HTTPException

from data.seed_data import CUSTOMERS

router = APIRouter()


@router.get("")
def list_customers():
    return CUSTOMERS


@router.get("/{customer_id}")
def get_customer(customer_id: str):
    customer = next((c for c in CUSTOMERS if c["customer_id"] == customer_id), None)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer
