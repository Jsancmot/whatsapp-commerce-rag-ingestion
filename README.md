# whatsapp-commerce-rag-ingestion

RAG ingestion pipeline for [WhatsApp Commerce SaaS](https://github.com/Jsancmot/whatsapp-commerce-backend).

This service is responsible for:
- Reading products from the PostgreSQL database
- Chunking product data into text documents
- Generating embeddings (Ollama locally, OpenAI in other environments)
- Writing vectors to the shared pgvector store

The backend service (`whatsapp-commerce-backend`) only **reads** the vector store. This service is the only writer.

## Architecture

```
[this service]       [whatsapp-commerce-backend]
   write -------------------- read
           PostgreSQL + pgvector
```

## Quickstart

```bash
# 1. Copy env file
cp .env.example .env
# Edit .env: set DATABASE_URL, OPENAI_API_KEY (if non-LOCAL), etc.

# 2. Run the ingestion pipeline (one-shot)
docker compose up --build

# 3. Force re-indexing (overwrites existing vectors)
# Edit docker-compose.yml and uncomment the --force command, then:
docker compose up --build
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `ENVIRONMENT` | `LOCAL` | `LOCAL` / `DEVELOPMENT` / `PREPRO` / `PRODUCTION` |
| `DATABASE_URL` | `postgresql://...@db:5432/...` | PostgreSQL connection string |
| `OPENAI_API_KEY` | `` | Required in non-LOCAL environments |
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434` | Ollama host (LOCAL only) |
| `OLLAMA_MODEL` | `llama3.2` | Ollama model for embeddings (LOCAL only) |
| `COLLECTION_NAME` | `whatsapp_commerce_rag` | pgvector collection name |
| `SCHEDULE_INTERVAL_MINUTES` | `0` | `0` = run once; `N` = loop every N mins |

## Improving the RAG

The main areas to iterate on are in `ingestion/chunking.py`:
- Change chunk strategy (sliding window, semantic splitting)
- Add new document sources (FAQ, store info, promotions)
- Tune chunk size and overlap

Embedding model changes go in `ingestion/embeddings.py`.
