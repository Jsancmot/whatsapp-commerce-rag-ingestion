
import asyncio
import logging
from ingestion.pipeline import run_pipeline
from ingestion.config import settings

logging.basicConfig(level=logging.INFO)

async def test():
    print("Testing run_pipeline...")
    summary = await run_pipeline(force=True)
    print(f"Summary: {summary}")

if __name__ == "__main__":
    asyncio.run(test())
