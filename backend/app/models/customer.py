"""Customer — project.md §17, §69."""

from typing import Optional

from sqlmodel import Field, SQLModel


class Customer(SQLModel, table=True):
    customer_id: str = Field(primary_key=True)
    name: str
    plan: str
    account_age_years: int
    recent_sentiment: str
    open_issues: int = 0
