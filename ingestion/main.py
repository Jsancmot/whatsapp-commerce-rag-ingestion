"""
Entrypoint for the RAG ingestion service.

Three execution modes (can be combined):

  SCHEDULER MODE (default):
    SCHEDULE_INTERVAL_MINUTES=0  → run once and exit (ideal for K8s CronJob / one-shot Docker)
    SCHEDULE_INTERVAL_MINUTES=N  → loop every N minutes (long-running container / sidecar)

  API MODE (event-driven):
    API_ENABLED=true → start a FastAPI server so the backend can trigger targeted
                       re-indexing immediately after product CRUD operations.
                       Can run alongside the scheduler or standalone.

  WORKER MODE (Redis queue):
    WORKER_ENABLED=true → start a Redis worker that listens for product change events
                         and triggers re-indexing automatically.

CLI flags:
  --force   → skip sync state and re-index every product from scratch
  --api     → override API_ENABLED=true via CLI (useful for local dev)
  --worker  → override WORKER_ENABLED=true via CLI
"""

import asyncio
import logging
import sys

# Configure logging early so it's active during imports
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

from ingestion.config import settings
from ingestion.pipeline import run_pipeline


async def run_scheduler(force: bool = False) -> None:
    """Run the pipeline on a recurring schedule."""
    interval = settings.SCHEDULE_INTERVAL_MINUTES
    logger.info(f"[main] Starting recurring scheduler every {interval} minutes.")
    
    while True:
        try:
            summary = await run_pipeline(force=force)
            logger.info(
                f"[main] Scheduler cycle done. Summary: {summary}. Next run in {interval} minutes..."
            )
        except Exception as e:
            logger.error(f"[main] Scheduler error: {e}")
            
        await asyncio.sleep(interval * 60)


async def run_api_server() -> None:
    """Start the FastAPI event-driven ingestion server."""
    import uvicorn
    from ingestion.api import app

    config = uvicorn.Config(
        app=app,
        host=settings.API_HOST,
        port=settings.API_PORT,
        log_level="info",
    )
    server = uvicorn.Server(config)
    logger.info(
        f"[main] Starting ingestion API on {settings.API_HOST}:{settings.API_PORT}"
    )
    await server.serve()


async def run_worker() -> None:
    """Start the Redis worker for event-driven updates."""
    from ingestion.worker import main as worker_main
    logger.info("[main] Starting Redis worker...")
    await worker_main()


async def main(force: bool = False, api_enabled: bool = False, worker_enabled: bool = False) -> None:
    # ── 1. Pre-flight health check ──────────────────────────────────────────
    from ingestion.embeddings import verify_embeddings_health

    if not await verify_embeddings_health():
        logger.error("[main] Pre-flight health check failed. Exiting.")
        sys.exit(1)

    # ── 2. Initial Sync ─────────────────────────────────────────────────────
    # We always run the pipeline once on startup to ensure the vector store
    # is in sync with the current database state.
    logger.info("[main] Performing initial sync of database...")
    try:
        summary = await run_pipeline(force=force)
        logger.info(f"[main] Initial sync complete. Summary: {summary}")
    except Exception as e:
        logger.error(f"[main] Initial sync failed: {e}")
        # We continue anyway if API or worker are enabled, as they might still work
        # but indexing existing data failed. 

    # ── 3. Post-sync Execution Modes ─────────────────────────────────────────
    tasks = []

    # A. Recurring Scheduler (if N > 0)
    if settings.SCHEDULE_INTERVAL_MINUTES > 0:
        tasks.append(asyncio.create_task(run_scheduler(force=force)))

    # B. API Server (Event-driven)
    if api_enabled or settings.API_ENABLED:
        tasks.append(asyncio.create_task(run_api_server()))

    # C. Redis Worker (Queue-driven)
    if worker_enabled or settings.WORKER_ENABLED:
        tasks.append(asyncio.create_task(run_worker()))

    if tasks:
        # Run all background services concurrently
        await asyncio.gather(*tasks)
    else:
        # If no background tasks and interval was 0, we already did the sync once, so we exit.
        logger.info("[main] One-shot sync completed. No persistent tasks enabled. Exiting.")


if __name__ == "__main__":
    force_flag = "--force" in sys.argv
    api_flag = "--api" in sys.argv or settings.API_ENABLED
    worker_flag = "--worker" in sys.argv or settings.WORKER_ENABLED
    asyncio.run(main(force=force_flag, api_enabled=api_flag, worker_enabled=worker_flag))
