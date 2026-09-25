"""Business records: the orders, payments, shipments and customers the department agents look things up in.

Seeded with the demo data; import your own (CSV or JSON) and every agent uses it immediately.
"""

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.services import business_data

router = APIRouter()


@router.get("/data")
def data():
    return business_data.snapshot()


@router.get("/orders/lookup")
def lookup(ref: str):
    """Exactly what the order desk does with what a caller says: "ORD-83921", "83921", "3921"."""
    return business_data.lookup_order(ref)


@router.post("/import")
async def import_data(file: UploadFile = File(...), kind: str | None = Form(None)):
    """CSV or JSON of orders (order_id,item,...), payments, shipments or customers; the kind is detected from the columns."""
    try:
        return business_data.import_records(file.filename or "data.csv", await file.read(), kind)
    except (ValueError, KeyError) as e:
        raise HTTPException(400, str(e)) from e
