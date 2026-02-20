"""
Entrypoint for the RAG ingestion service.

Modes (controlled via SCHEDULE_INTERVAL_MINUTES env var):
  - 0 (default) -> run once and exit (ideal for Kubernetes CronJob or one-shot Docker)
  - N > 0       -> loop every N minutes (long-running container / sidecar)

CLI flags:
  --force   -> skip the emptiness check and always re-index
"""
import asyncio
import logging
import sys
import time

from ingestion.config import settings
from ingestion.pipeline import run_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main(force: bool = False) -> None:
    interval = settings.SCHEDULE_INTERVAL_MINUTES

    if interval == 0:
        logger.info("[main] Running pipeline once (SCHEDULE_INTERVAL_MINUTES=0).")
        await run_pipeline(force=force)
        logger.info("[main] Done.")
    else:
        logger.info(f"[main] Running pipeline every {interval} minutes.")
        while True:
            await run_pipeline(force=force)
            logger.info(f"[main] Next run in {interval} minutes...")
            time.sleep(interval * 60)


if __name__ == "__main__":
    force_flag = "--force" in sys.argv
    asyncio.run(main(force=force_flag))
