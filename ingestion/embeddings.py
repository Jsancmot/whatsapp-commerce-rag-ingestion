"""
Embedding model factory.

Returns the appropriate embedding model based on the environment:
- LOCAL  -> OllamaEmbeddings (no API key required)
- Others -> OpenAIEmbeddings (text-embedding-3-small)
"""

from ingestion.config import settings


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
