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
        logger.info(f"[embeddings] Jina AI configured with model '{settings.JINA_MODEL}'")
        return True
    
    elif provider == "openai":
        if not settings.OPENAI_API_KEY:
            logger.error("[embeddings] OPENAI_API_KEY is not set.")
            return False
        logger.info("[embeddings] OpenAI configured with model 'text-embedding-3-small'")
        return True
    
    elif provider == "ollama":
        logger.info(
            f"[embeddings] Verifying Ollama health at {settings.OLLAMA_BASE_URL}..."
        )
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
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

                models = response.json().get("models", [])
                model_names = [m.get("name") for m in models]

                target = settings.OLLAMA_EMBED_MODEL
                target_versions = [target]
                if ":" not in target:
                    target_versions.append(f"{target}:latest")

                if any(name in target_versions for name in model_names):
                    logger.info(
                        f"[embeddings] Ollama model '{settings.OLLAMA_EMBED_MODEL}' is ready."
                    )
                    return True
                else:
                    logger.error(
                        f"[embeddings] Model '{settings.OLLAMA_EMBED_MODEL}' NOT FOUND in Ollama. "
                        f"Please run 'ollama pull {settings.OLLAMA_EMBED_MODEL}'."
                    )
                    return False

        except Exception as e:
            logger.error(f"[embeddings] Unexpected error during health check: {str(e)}")
            return False
    
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
    
    elif provider == "ollama":
        from langchain_ollama import OllamaEmbeddings

        return OllamaEmbeddings(
            model=settings.OLLAMA_EMBED_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
        )
    
    else:
        raise ValueError(f"Unknown EMBEDDING_PROVIDER: {provider}")
