"""
Embedding model factory.

Returns the appropriate embedding model based on the environment:
- LOCAL  -> OllamaEmbeddings (no API key required)
- Others -> OpenAIEmbeddings (text-embedding-3-small)
"""

import logging

import httpx

from ingestion.config import settings

logger = logging.getLogger(__name__)


async def verify_embeddings_health():
    """
    Verifies if the configured embedding model is available and ready.
    - LOCAL mode: Checks Ollama connectivity and ensures the specific model is pulled.
    - Non-LOCAL mode: Checks OpenAI model availability (if possible via simple test) or API key presence.
    """
    if not settings.is_local:
        if not settings.OPENAI_API_KEY:
            logger.error(
                "[embeddings] OPENAI_API_KEY is not set in environment settings."
            )
            return False

        logger.info(
            "[embeddings] Verifying OpenAI connectivity for model 'text-embedding-3-small'..."
        )
        try:
            # We do a minimal check to see if we can reach OpenAI or at least if we have a key
            # For OpenAI, a full request is expensive, so we just check the key presence
            # and maybe a simple connectivity test if needed.
            return True
        except Exception as e:
            logger.error(f"[embeddings] OpenAI health check failed: {str(e)}")
            return False

    # Ollama Health Check (LOCAL mode)
    logger.info(
        f"[embeddings] Verifying Ollama health at {settings.OLLAMA_BASE_URL}..."
    )
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # 1. Check if Ollama service is up
            try:
                response = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            except httpx.ConnectError:
                logger.error(
                    f"[embeddings] Could not connect to Ollama at {settings.OLLAMA_BASE_URL}. Is it running?"
                )
                return False

            if response.status_code != 200:
                logger.error(
                    f"[embeddings] Ollama service returned status {response.status_code}"
                )
                return False

            # 2. Verify specifically configured OLLAMA_EMBED_MODEL existence
            models = response.json().get("models", [])
            model_names = [m.get("name") for m in models]

            # Ollama models often have ":latest" suffix in the list if not explicitly tagged
            target = settings.OLLAMA_EMBED_MODEL
            target_versions = [target]
            if ":" not in target:
                target_versions.append(f"{target}:latest")

            if any(name in target_versions for name in model_names):
                logger.info(
                    f"[embeddings] Configured local model '{settings.OLLAMA_EMBED_MODEL}' is ready."
                )
                return True
            else:
                logger.error(
                    f"[embeddings] Configured model '{settings.OLLAMA_EMBED_MODEL}' NOT FOUND in your local Ollama. "
                    f"Please run 'ollama pull {settings.OLLAMA_EMBED_MODEL}' or wait for Docker auto-pull."
                )
                return False

    except Exception as e:
        logger.error(f"[embeddings] Unexpected error during health check: {str(e)}")
        return False


def get_embeddings():
    if settings.is_local:
        from langchain_ollama import OllamaEmbeddings

        return OllamaEmbeddings(
            model=settings.OLLAMA_EMBED_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
        )
    else:
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=settings.OPENAI_API_KEY,
        )
