"""
Entrypoint for the RAG ingestion service.

Two execution modes (can be combined):

  SCHEDULER MODE (default):
    SCHEDULE_INTERVAL_MINUTES=0  → run once and exit (ideal for K8s CronJob / one-shot Docker)
    SCHEDULE_INTERVAL_MINUTES=N  → loop every N minutes (long-running container / sidecar)

  API MODE (event-driven):
    API_ENABLED=true → start a FastAPI server so the backend can trigger targeted
                       re-indexing immediately after product CRUD operations.
                       Can run alongside the scheduler or standalone.

CLI flags:
  --force   → skip sync state and re-index every product from scratch
  --api     → override API_ENABLED=true via CLI (useful for local dev)
"""

import asyncio
import logging
import sys

from ingestion.config import settings
from ingestion.pipeline import run_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def run_scheduler(force: bool = False) -> None:
    """Run the pipeline once or on a recurring schedule."""
    interval = settings.SCHEDULE_INTERVAL_MINUTES

    if interval == 0:
        logger.info("[main] Running pipeline once (SCHEDULE_INTERVAL_MINUTES=0).")
        summary = await run_pipeline(force=force)
        logger.info(f"[main] Done. Summary: {summary}")
    else:
        logger.info(f"[main] Running pipeline every {interval} minutes.")
        while True:
            summary = await run_pipeline(force=force)
            logger.info(
                f"[main] Cycle done. Summary: {summary}. Next run in {interval} minutes..."
            )
            # Use asyncio.sleep so the API server stays responsive during the wait
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


async def main(force: bool = False, api_enabled: bool = False) -> None:
    tasks = []

    if settings.SCHEDULE_INTERVAL_MINUTES == 0 and not api_enabled:
        # Simple one-shot mode: run pipeline and exit
        await run_scheduler(force=force)
        return

    # One or both of scheduler + API server run concurrently
    if settings.SCHEDULE_INTERVAL_MINUTES > 0:
        tasks.append(asyncio.create_task(run_scheduler(force=force)))

    if api_enabled or settings.API_ENABLED:
        tasks.append(asyncio.create_task(run_api_server()))

    if tasks:
        await asyncio.gather(*tasks)
    else:
        # Fallback: just run once
        await run_scheduler(force=force)


if __name__ == "__main__":
    force_flag = "--force" in sys.argv
    api_flag = "--api" in sys.argv or settings.API_ENABLED
    asyncio.run(main(force=force_flag, api_enabled=api_flag))
