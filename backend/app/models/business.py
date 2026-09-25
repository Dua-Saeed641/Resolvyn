"""Business records the department agents read and change: orders, payments, shipments, account state.

These are the system of record for "what is happening with this customer's order". They are seeded with the demo
data (data/seed_data.py) and can be extended with your own data: Team console → Knowledge → Business data, or
`scripts/import_business_data.py`. Replace app/tools/mock_apis.py with real API calls to connect a live system.
"""

from typing import Optional

from sqlmodel import Field, SQLModel


class Order(SQLModel, table=True):
    __tablename__ = "business_orders"

    order_id: str = Field(primary_key=True)  # ORD-83921
    customer_id: Optional[str] = Field(default=None, index=True)
    item: str = ""
    amount: int = 0
    placed: str = ""  # ISO date, e.g. 2026-09-20
    status: str = "Confirmed"  # Processing | Confirmed | Shipped | Delivered | Cancelled
    shipment_id: Optional[str] = None


class Payment(SQLModel, table=True):
    __tablename__ = "business_payments"

    transaction_id: str = Field(primary_key=True)  # TXN-90112
    order_id: str = Field(index=True)
    amount: int = 0
    status: str = "SUCCESS"  # SUCCESS | FAILED | PENDING
    method: str = ""
    timestamp: str = ""


class Shipment(SQLModel, table=True):
    __tablename__ = "business_shipments"

    shipment_id: str = Field(primary_key=True)  # SHP-5521
    carrier: str = ""
    status: str = "In transit"
    location: str = ""
    eta: str = ""
    delayed: bool = False
    delay_reason: Optional[str] = None


class AccountState(SQLModel, table=True):
    __tablename__ = "business_accounts"

    customer_id: str = Field(primary_key=True)
    status: str = "ACTIVE"  # ACTIVE | LOCKED
    failed_logins: int = 0
    locked_reason: Optional[str] = None
