"""
SQLModel definition for Product - mirrors the backend's app/models.py.

The ingestion service reads the same PostgreSQL database as the backend.
We keep a local copy of only the fields needed for ingestion to avoid
coupling this service to the backend package.

IMPORTANT: Keep this in sync with the backend's Product model when
structural changes (column adds/renames) are made.
"""
from typing import Optional
from sqlmodel import Field, SQLModel


class Product(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: str
    price: float
    category: str
    stock: int = 100
    is_available: bool = True
