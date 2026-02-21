"""
Text chunking strategies for product documents.

Current strategy: one flat chunk per product (name + description + price + category + stock).
This is intentionally simple for a product catalog where each item is self-contained.

Future improvements:
- RecursiveCharacterTextSplitter for long descriptions or multi-section docs
- Semantic chunking for FAQ documents
- Sliding window for dense content like ingredient lists
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class Document:
    text: str
    metadata: dict[str, Any]
    # Deterministic ID derived from the source record — used for upsert in pgvector.
    # Format: "product-{id}" so multiple sources (products, faqs…) never collide.
    doc_id: str = ""


def chunk_products(products: list) -> list[Document]:
    """
    Converts a list of Product ORM objects into a list of Documents
    ready to be embedded and stored in the vector store.

    Each product becomes a single chunk with a rich text representation
    that maximises retrieval accuracy for natural-language queries.

    Key design decisions:
    - `stock` is included so the LLM can answer availability questions.
    - `version` in metadata lets the pipeline skip unchanged products.
    - `source` = "products" allows multi-source pipelines to filter/delete
      by source without touching other collections' documents.
    """
    docs = []
    for p in products:
        # Determine availability label
        stock_label = (
            f"{p.stock} unidades disponibles"
            if p.stock > 0
            else "Agotado temporalmente"
        )

        text = (
            f"Producto: {p.name}\n"
            f"Descripcion: {p.description}\n"
            f"Precio: {p.price}EUR\n"
            f"Categoria: {p.category}\n"
            f"Disponibilidad: {stock_label}"
        )
        metadata = {
            "source": "products",
            "product_id": p.id,
            "name": p.name,
            "category": p.category,
            "price": float(p.price),
            "stock": p.stock,
            "version": getattr(p, "version", 1),
        }
        docs.append(Document(text=text, metadata=metadata, doc_id=f"product-{p.id}"))
    return docs


def chunk_store_settings(settings_rows: list) -> list[Document]:
    """
    Converts StoreSetting rows into Documents for vector store indexing.

    StoreSetting rows typically hold FAQ-style information:
      - store_name, address, opening_hours, payment_methods, etc.

    Each row becomes one Document with a deterministic ID "setting-{key}",
    so re-running the pipeline is idempotent (pgvector upserts by ID).
    """
    docs = []
    for row in settings_rows:
        text = f"Informacion de la tienda — {row.key}: {row.value}"
        if row.description:
            text += f"\nDetalles: {row.description}"

        metadata = {
            "source": "store_settings",
            "setting_key": row.key,
        }
        docs.append(Document(text=text, metadata=metadata, doc_id=f"setting-{row.key}"))
    return docs
