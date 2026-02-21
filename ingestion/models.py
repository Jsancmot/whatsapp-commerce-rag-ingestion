"""
SQLModel definitions for the ingestion service.

Product mirrors the backend's app/models.py (only the fields needed for ingestion).
IngestionSyncState is internal to the ingestion service and tracks which products
have been embedded and at which `version`, enabling incremental sync.

IMPORTANT: Keep Product in sync with the backend's Product model when
structural changes (column adds/renames) are made.
"""

from datetime import datetime
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
    version: int = Field(default=1)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class IngestionSyncState(SQLModel, table=True):
    """
    Tracks the last-synced version for each product in the vector store.

    This table is the source of truth for incremental sync:
    - If a product's current `version` > stored `synced_version` → re-index.
    - If a product_id is in the table but not in the active SQL products → delete
      the vector store embedding and this row.
    - If a product_id is NOT in the table → it's new, add it.
    """

    __tablename__ = "ingestion_sync_state"

    product_id: int = Field(primary_key=True)
    synced_version: int = Field(default=0)
    synced_at: datetime = Field(default_factory=datetime.utcnow)
