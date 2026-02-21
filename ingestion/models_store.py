"""
SQLModel mirror of the StoreSetting model from the backend.

StoreSetting holds FAQ-style key/value pairs (store_name, address,
opening_hours, payment_methods, etc.) that are useful for the RAG chatbot.

IMPORTANT: Keep in sync with the backend's StoreSetting model in app/models.py.
"""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class StoreSetting(SQLModel, table=True):
    __tablename__ = "storesetting"

    id: Optional[int] = Field(default=None, primary_key=True)
    key: str = Field(index=True, unique=True)
    value: str
    description: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)
