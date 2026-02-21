"""
FastAPI application for event-driven ingestion.

The backend calls this API whenever a product is created, updated, or deleted,
triggering an immediate targeted re-index for that specific product instead of
waiting for the next scheduled run.

Endpoints:
  POST /ingest              → Full incremental sync (same as running the pipeline manually)
  POST /ingest/{product_id} → Re-index a single product (fastest path, event-driven)
  GET  /health              → Health check
  GET  /status              → Returns last sync summary
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query

from ingestion.pipeline import run_pipeline

logger = logging.getLogger(__name__)

# In-memory cache of the last pipeline run result (for the /status endpoint).
_last_summary: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("[api] Ingestion API server started.")
    yield
    logger.info("[api] Ingestion API server shutting down.")


app = FastAPI(
    title="WhatsApp Commerce — RAG Ingestion API",
    description=(
        "Internal HTTP API that allows the backend to trigger targeted re-indexing "
        "of products into the vector store without waiting for the next scheduled run."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health() -> dict:
    """Simple liveness probe."""
    return {"status": "ok"}


@app.get("/status")
async def status() -> dict:
    """Returns the summary of the last pipeline run."""
    return {"last_run": _last_summary or "No pipeline run recorded yet."}


@app.post("/ingest")
async def ingest_all(
    force: bool = Query(
        default=False, description="Re-index all products, ignoring sync state"
    ),
) -> dict:
    """
    Trigger a full incremental sync.

    - Without `force`: only processes new, changed, or removed products.
    - With `force=true`: re-embeds every active product from scratch.

    Use this endpoint for scheduled syncs or manual admin triggers.
    """
    global _last_summary
    logger.info(f"[api] POST /ingest called (force={force})")
    try:
        summary = await run_pipeline(force=force)
        _last_summary = summary
        return {"ok": True, "summary": summary}
    except Exception as e:
        logger.error(f"[api] Pipeline error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ingest/{product_id}")
async def ingest_product(product_id: int) -> dict:
    """
    Re-index a single product by ID.

    The backend calls this endpoint immediately after creating/updating/deleting
    a product, so the vector store stays in sync in near-real-time.

    - If the product is active → re-embed it (upsert).
    - If the product is disabled/deleted in SQL → remove its embedding.
    """
    global _last_summary
    logger.info(f"[api] POST /ingest/{product_id} called")
    try:
        summary = await run_pipeline(product_id=product_id)
        _last_summary = summary
        return {"ok": True, "product_id": product_id, "summary": summary}
    except Exception as e:
        logger.error(f"[api] Pipeline error for product_id={product_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
