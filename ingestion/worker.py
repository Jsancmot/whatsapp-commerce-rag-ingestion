"""
Redis worker for event-driven RAG updates.

Listens to the Redis queue for product change events and triggers
targeted re-indexing when products are created, updated, or deleted.
"""

import asyncio
import json
import logging
import signal
import sys

import redis.asyncio as redis

from ingestion.config import settings
from ingestion.pipeline import run_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


class RAGWorker:
    def __init__(self):
        self.redis_client: redis.Redis | None = None
        self.running = True

    async def connect(self):
        self.redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
        logger.info(f"[worker] Connected to Redis at {settings.REDIS_URL}")

    async def disconnect(self):
        if self.redis_client:
            await self.redis_client.close()
            logger.info("[worker] Disconnected from Redis")

    async def process_message(self, message: dict):
        """
        Process a product update message.

        Expected message format:
        {
            "event": "product_created" | "product_updated" | "product_deleted",
            "product_id": 123,
            "timestamp": "2026-01-01T00:00:00Z"
        }

        Note: For all event types, we call run_pipeline with product_id.
        If the product is deleted/disabled, the pipeline detects it and removes
        the embedding from the vector store.
        """
        event = message.get("event")
        product_id = message.get("product_id")

        logger.info(f"[worker] Processing {event} for product_id={product_id}")

        try:
            summary = await run_pipeline(product_id=product_id)
            logger.info(f"[worker] Successfully processed {event}: {summary}")
            return True

        except Exception as e:
            logger.error(
                f"[worker] Error processing {event} for product_id={product_id}: {e}"
            )
            return False

    async def run(self):
        """Main worker loop - listens to Redis queue."""
        await self.connect()

        logger.info(f"[worker] Listening on queue '{settings.REDIS_QUEUE_NAME}'...")

        while self.running:
            try:
                # Blocking pop from queue (wait up to 5 seconds)
                result = await self.redis_client.blpop(
                    settings.REDIS_QUEUE_NAME, timeout=5
                )

                if result is None:
                    continue

                # result is tuple: (queue_name, message)
                _, message = result

                try:
                    data = json.loads(message)
                    await self.process_message(data)
                except json.JSONDecodeError as e:
                    logger.error(f"[worker] Invalid JSON message: {e}")

            except Exception as e:
                logger.error(f"[worker] Error in worker loop: {e}")
                await asyncio.sleep(1)  # Brief pause before retrying

    def stop(self):
        """Graceful shutdown."""
        logger.info("[worker] Shutting down...")
        self.running = False


async def main():
    worker = RAGWorker()

    # Graceful shutdown handlers
    loop = asyncio.get_event_loop()

    def signal_handler():
        worker.stop()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)

    try:
        await worker.run()
    finally:
        await worker.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
