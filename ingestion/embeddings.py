"""
Embedding model factory.

Returns the appropriate embedding model based on the EMBEDDING_PROVIDER setting:
- ollama   -> OllamaEmbeddings (LOCAL mode, no API key)
- jina     -> JinaEmbeddings (production, requires JINA_API_KEY)
- openai   -> OpenAIEmbeddings (legacy)
"""

import logging

import httpx

from ingestion.config import settings

logger = logging.getLogger(__name__)


async def verify_embeddings_health():
    """
    Verifies if the configured embedding model is available and ready.
    """
    provider = settings.EMBEDDING_PROVIDER.lower()

    if provider == "jina":
        if not settings.JINA_API_KEY:
            logger.error("[embeddings] JINA_API_KEY is not set.")
            return False
        logger.info(
            f"[embeddings] Jina AI configured with model '{settings.JINA_MODEL}'"
        )
        return True

    elif provider == "openai":
        if not settings.OPENAI_API_KEY:
            logger.error("[embeddings] OPENAI_API_KEY is not set.")
            return False
        logger.info(
            "[embeddings] OpenAI configured with model 'text-embedding-3-small'"
        )
        return True

    else:
        logger.error(f"[embeddings] Unknown provider: {provider}")
        return False


def get_embeddings():
    provider = settings.EMBEDDING_PROVIDER.lower()

    if provider == "jina":
        from langchain_community.embeddings import JinaEmbeddings

        return JinaEmbeddings(
            model=settings.JINA_MODEL,
            jina_api_key=settings.JINA_API_KEY,
        )

    elif provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=settings.OPENAI_API_KEY,
        )

    else:
        raise ValueError(f"Unknown EMBEDDING_PROVIDER: {provider}")
