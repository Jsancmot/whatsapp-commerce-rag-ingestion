from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    ENVIRONMENT: str = "LOCAL"  # LOCAL | DEVELOPMENT | PREPRO | PRODUCTION

    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@db:5432/whatsapp_commerce"

    # OpenAI (non-LOCAL environments - legacy)
    OPENAI_API_KEY: str = ""

    # Jina AI Embeddings (PRIMARY for non-LOCAL)
    JINA_API_KEY: str = ""
    JINA_MODEL: str = "jina-embeddings-v3"

    # Ollama (LOCAL environment only)
    OLLAMA_BASE_URL: str = "http://host.docker.internal:11434"
    OLLAMA_MODEL: str = "llama3.2"
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"

    # Embedding provider selection
    # Use: "jina" (production), "openai" (legacy), "ollama" (local)
    EMBEDDING_PROVIDER: str = "ollama"

    # Redis for event-driven updates
    REDIS_URL: str = "redis://redis:6379/0"
    REDIS_QUEUE_NAME: str = "rag:product-updates"

    # Vector store
    COLLECTION_NAME: str = "whatsapp_commerce_rag"

    # Scheduler: 0 = run once and exit, N = loop every N minutes
    SCHEDULE_INTERVAL_MINUTES: int = 0

    # Multi-source: also index StoreSetting rows from the backend DB
    INGEST_STORE_SETTINGS: bool = True

    # HTTP API (event-driven mode)
    # Set API_ENABLED=true to expose a FastAPI server that the backend can call
    # to trigger a targeted re-index when a product changes.
    API_ENABLED: bool = True
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8001

    # Redis worker (event-driven mode)
    # Set WORKER_ENABLED=true to listen for product change events from Redis
    WORKER_ENABLED: bool = True

    @property
    def is_local(self) -> bool:
        return self.ENVIRONMENT.upper() == "LOCAL"

    @property
    def async_database_url(self) -> str:
        """asyncpg driver URL for langchain-postgres async mode."""
        return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")


settings = Settings()
