-- 01_schema.sql
-- Creates the tables required by the RAG ingestion service in LOCAL mode.
-- This mirrors the SQLModel definitions in ingestion/models.py and models_store.py.
-- PostgreSQL init scripts run in alphabetical order on first DB start.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS product (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT NOT NULL,
    price       FLOAT NOT NULL,
    category    TEXT NOT NULL,
    stock       INTEGER NOT NULL DEFAULT 100,
    is_available BOOLEAN NOT NULL DEFAULT TRUE,
    version     INTEGER NOT NULL DEFAULT 1,
    updated_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS storesetting (
    id          SERIAL PRIMARY KEY,
    key         TEXT NOT NULL UNIQUE,
    value       TEXT NOT NULL,
    description TEXT,
    updated_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ingestion_sync_state (
    product_id      INTEGER PRIMARY KEY,
    synced_version  INTEGER NOT NULL DEFAULT 0,
    synced_at       TIMESTAMP NOT NULL DEFAULT NOW()
);
