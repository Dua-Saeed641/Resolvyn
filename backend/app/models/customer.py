"""Customer — project.md §17, §69."""

from typing import Optional

from sqlmodel import Field, SQLModel


class Customer(SQLModel, table=True):
    customer_id: str = Field(primary_key=True)
    name: str
    email: Optional[str] = None
    phone_last4: Optional[str] = None
    plan: str = "Standard"
    account_age_years: int = 0
    recent_sentiment: str = "Neutral"
    open_issues: int = 0
    previous_tickets: int = 0
