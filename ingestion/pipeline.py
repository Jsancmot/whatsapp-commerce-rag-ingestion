"""
Main ingestion pipeline.

Flow:
  1. Read all active products from PostgreSQL (SQLModel)
  2. Chunk each product into a Document (see chunking.py)
  3. Check if the vector store already has data
  4. Write embeddings to pgvector via langchain-postgres

Usage:
  await run_pipeline()           # run once
  await run_pipeline(force=True) # skip empty-check and always re-index
"""
import logging

from langchain_postgres import PGVector
from sqlmodel import Session, create_engine, select

from ingestion.chunking import chunk_products
from ingestion.config import settings
from ingestion.embeddings import get_embeddings
from ingestion.models import Product

logger = logging.getLogger(__name__)


def _get_vector_store(embeddings) -> PGVector:
    return PGVector(
        embeddings=embeddings,
        collection_name=settings.COLLECTION_NAME,
        connection=settings.async_database_url,
        use_jsonb=True,
        async_mode=True,
        create_extension=False,
    )


async def run_pipeline(force: bool = False) -> None:
    """
    Execute the full ingestion pipeline.

    Args:
        force: If True, skip the emptiness check and always re-index all products.
    """
    logger.info("[pipeline] Starting RAG ingestion pipeline...")

    # 1. Fetch products from SQL
    engine = create_engine(settings.DATABASE_URL)
    with Session(engine) as session:
        products = session.exec(select(Product).where(Product.is_available == True)).all()  # noqa: E712

    if not products:
        logger.warning("[pipeline] No products found in SQL database. Nothing to ingest.")
        return

    logger.info(f"[pipeline] Found {len(products)} products in SQL database.")

    # 2. Initialise embeddings and vector store
    embeddings = get_embeddings()
    vector_store = _get_vector_store(embeddings)

    # 3. Check if vector store already has data (skip if force=True)
    if not force:
        try:
            existing = await vector_store.asimilarity_search("producto", k=1)
            if existing:
                logger.info("[pipeline] Vector store already contains data. Skipping. Use force=True to re-index.")
                return
        except Exception as e:
            logger.warning(f"[pipeline] Could not check vector store state: {e}. Proceeding with ingestion.")

    # 4. Chunk and embed
    docs = chunk_products(products)
    texts = [d.text for d in docs]
    metadatas = [d.metadata for d in docs]

    logger.info(f"[pipeline] Embedding and indexing {len(docs)} documents...")
    await vector_store.aadd_texts(texts, metadatas=metadatas)
    logger.info("[pipeline] Ingestion pipeline completed successfully.")
