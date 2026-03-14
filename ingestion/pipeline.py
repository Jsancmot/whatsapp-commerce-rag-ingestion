"""
Main ingestion pipeline — incremental sync edition.

Flow:
  1. Fetch all active products from PostgreSQL.
  2. Load IngestionSyncState to know what was last indexed and at which version.
  3. Compute a three-way diff:
       - NEW     → product in SQL but not in sync state → embed and add to sync state.
       - CHANGED → product in SQL AND in sync state, but version increased → delete old
                   embedding + re-embed + update sync state.
       - REMOVED → product_id in sync state but NOT in active SQL products (disabled or
                   deleted) → delete embedding + remove from sync state.
       - UNCHANGED → skip (no vector store write, no token cost).
  4. Optionally index StoreSetting rows (store info, FAQ-style data).

Usage:
  await run_pipeline()            # incremental — only processes changes
  await run_pipeline(force=True)  # full re-index regardless of sync state
  await run_pipeline(product_id=5) # sync a single product (event-driven mode)
"""

import logging
from datetime import datetime

from langchain_postgres import PGVector
from sqlmodel import Session, create_engine, select

from ingestion.chunking import chunk_products, chunk_store_settings, Document
from ingestion.config import settings
from ingestion.embeddings import get_embeddings
from ingestion.models import IngestionSyncState, Product
from ingestion.models_store import StoreSetting

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Vector store factory
# ---------------------------------------------------------------------------


def _get_vector_store(embeddings) -> PGVector:
    return PGVector(
        embeddings=embeddings,
        collection_name=settings.COLLECTION_NAME,
        connection=settings.async_database_url,
        use_jsonb=True,
        async_mode=True,
        create_extension=False,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _upsert_docs(vector_store: PGVector, docs: list[Document]) -> None:
    """
    Upsert documents into the vector store using deterministic IDs.
    PGVector will replace any existing document with the same ID,
    preventing duplicates even when --force is used.
    """
    if not docs:
        return
    await vector_store.aadd_texts(
        texts=[d.text for d in docs],
        metadatas=[d.metadata for d in docs],
        ids=[d.doc_id for d in docs],
    )


async def _delete_by_product_ids(
    vector_store: PGVector, product_ids: list[int]
) -> None:
    """Delete all vector store documents whose metadata.product_id is in the given list."""
    for pid in product_ids:
        try:
            await vector_store.adelete(filter={"product_id": pid})
            logger.info(f"[pipeline] Deleted vector doc for product_id={pid}")
        except Exception as e:
            logger.warning(
                f"[pipeline] Could not delete vector doc for product_id={pid}: {e}"
            )


def _load_sync_state(session: Session) -> dict[int, int]:
    """Returns a mapping {product_id: synced_version} from the sync state table."""
    rows = session.exec(select(IngestionSyncState)).all()
    return {row.product_id: row.synced_version for row in rows}


def _update_sync_state(session: Session, product_id: int, version: int) -> None:
    existing = session.get(IngestionSyncState, product_id)
    if existing:
        existing.synced_version = version
        existing.synced_at = datetime.utcnow()
        session.add(existing)
    else:
        session.add(IngestionSyncState(product_id=product_id, synced_version=version))


def _delete_sync_state(session: Session, product_id: int) -> None:
    existing = session.get(IngestionSyncState, product_id)
    if existing:
        session.delete(existing)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def run_pipeline(force: bool = False, product_id: int | None = None) -> dict:
    """
    Execute the ingestion pipeline.

    Args:
        force:      If True, re-index every active product regardless of version.
        product_id: If provided, only sync that specific product (event-driven mode).

    Returns:
        A summary dict with counts for observability / API responses.
    """
    logger.info(
        "[pipeline] Starting RAG ingestion pipeline"
        f" (force={force}, product_id={product_id})"
    )

    engine = create_engine(settings.DATABASE_URL)
    summary = {"added": 0, "updated": 0, "removed": 0, "skipped": 0, "errors": 0}

    with Session(engine) as session:
        # ── Ensure all required tables exist ────────────────────────────────
        # We always ensure IngestionSyncState exists. In LOCAL/DEVELOPMENT,
        # we can also create other tables if they are missing.
        from sqlmodel import SQLModel
        SQLModel.metadata.create_all(engine)
        logger.debug("[pipeline] Ensured all tables exist via create_all.")

        # ── 1. Fetch active products from SQL ────────────────────────────────
        stmt = select(Product).where(Product.is_available == True)  # noqa: E712
        if product_id is not None:
            stmt = stmt.where(Product.id == product_id)
        active_products = session.exec(stmt).all()

        if not active_products and product_id is not None:
            # Single-product mode: product was disabled or deleted → remove from VS
            logger.info(
                f"[pipeline] Product {product_id} not active → removing from vector store."
            )
            embeddings = get_embeddings()
            vector_store = _get_vector_store(embeddings)
            await _delete_by_product_ids(vector_store, [product_id])
            _delete_sync_state(session, product_id)
            session.commit()
            summary["removed"] = 1
            return summary

        if not active_products:
            logger.warning("[pipeline] No active products found. Nothing to ingest.")
            return summary

        logger.info(f"[pipeline] Found {len(active_products)} active products in SQL.")

        # ── 2. Load sync state ────────────────────────────────────────────────
        sync_state = _load_sync_state(session) if not force else {}
        active_ids = {p.id for p in active_products}

        # ── 3. Compute diff ───────────────────────────────────────────────────
        to_add: list[Product] = []
        to_update: list[Product] = []
        ids_to_delete_from_vs: list[int] = []

        for product in active_products:
            if product.id not in sync_state:
                to_add.append(product)
            elif force or product.version > sync_state[product.id]:
                to_update.append(product)
            else:
                summary["skipped"] += 1

        # Products in sync state but no longer active → remove from vector store
        if not force and product_id is None:
            removed_ids = [pid for pid in sync_state if pid not in active_ids]
            ids_to_delete_from_vs.extend(removed_ids)

        logger.info(
            f"[pipeline] Diff — NEW:{len(to_add)} CHANGED:{len(to_update)} "
            f"REMOVED:{len(ids_to_delete_from_vs)} SKIPPED:{summary['skipped']}"
        )

        if not to_add and not to_update and not ids_to_delete_from_vs:
            logger.info("[pipeline] Vector store is already up to date. Nothing to do.")
            return summary

        # ── 4. Apply changes to vector store ──────────────────────────────────
        embeddings = get_embeddings()
        vector_store = _get_vector_store(embeddings)

        # Delete stale embeddings (removed products + updated products)
        stale_ids = ids_to_delete_from_vs + [p.id for p in to_update]
        if stale_ids:
            await _delete_by_product_ids(vector_store, stale_ids)

        # Embed and upsert new + updated products
        products_to_embed = to_add + to_update
        if products_to_embed:
            logger.info(f"[pipeline] Embedding {len(products_to_embed)} documents...")
            try:
                docs = chunk_products(products_to_embed)
                await _upsert_docs(vector_store, docs)
                # Update sync state
                for p in products_to_embed:
                    _update_sync_state(session, p.id, p.version)
                summary["added"] += len(to_add)
                summary["updated"] += len(to_update)
            except Exception as e:
                logger.error(f"[pipeline] Error embedding products: {e}")
                summary["errors"] += 1

        # Remove sync state for deleted/disabled products
        for pid in ids_to_delete_from_vs:
            _delete_sync_state(session, pid)
        if ids_to_delete_from_vs:
            summary["removed"] += len(ids_to_delete_from_vs)

        session.commit()

    # ── 5. (Optional) Index StoreSetting data ─────────────────────────────────
    if product_id is None and settings.INGEST_STORE_SETTINGS:
        await _ingest_store_settings(engine, embeddings, vector_store)

    logger.info(f"[pipeline] Completed. Summary: {summary}")
    return summary


async def _ingest_store_settings(engine, embeddings, vector_store: PGVector) -> None:
    """
    Index StoreSetting rows (store info, FAQs) into the vector store.

    This is idempotent because we always use deterministic doc_ids
    (e.g. "setting-{key}") which PGVector will replace on re-run.
    """
    try:
        with Session(engine) as session:
            settings_rows = session.exec(select(StoreSetting)).all()

        if not settings_rows:
            logger.info("[pipeline] No StoreSetting rows found. Skipping.")
            return

        logger.info(f"[pipeline] Indexing {len(settings_rows)} StoreSetting rows...")
        docs = chunk_store_settings(settings_rows)
        await _upsert_docs(vector_store, docs)
        logger.info("[pipeline] StoreSetting indexing complete.")
    except Exception as e:
        logger.warning(f"[pipeline] Could not index StoreSetting: {e}")
