"""
Text chunking strategies for product documents.

Current strategy: one flat chunk per product (name + description + price + category).
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


def chunk_products(products: list) -> list[Document]:
    """
    Converts a list of Product ORM objects into a list of Documents
    ready to be embedded and stored in the vector store.

    Each product becomes a single chunk with a rich text representation
    that maximises retrieval accuracy for natural-language queries.
    """
    docs = []
    for p in products:
        text = (
            f"Producto: {p.name}\n"
            f"Descripcion: {p.description}\n"
            f"Precio: {p.price}EUR\n"
            f"Categoria: {p.category}"
        )
        metadata = {
            "product_id": p.id,
            "name": p.name,
            "category": p.category,
            "price": float(p.price),
        }
        docs.append(Document(text=text, metadata=metadata))
    return docs
