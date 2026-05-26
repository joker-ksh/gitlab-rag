-- Phase 3 — Supabase Schema
-- Run this in the Supabase SQL editor BEFORE running the ingest script.
-- If re-running, execute the DROP statements first, then the full file.

-- ── Drop existing objects (safe to run on a fresh project too) ───────────────
DROP FUNCTION IF EXISTS hybrid_search CASCADE;
DROP TABLE IF EXISTS chunks CASCADE;

-- ── Extensions ───────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS vector;

-- ── Table ────────────────────────────────────────────────────────────────────
CREATE TABLE chunks (
    id          BIGSERIAL PRIMARY KEY,
    content     TEXT NOT NULL,
    description TEXT,
    heading     TEXT,
    url         TEXT,
    embedding   VECTOR(768),
    fts_vector  TSVECTOR
        GENERATED ALWAYS AS (to_tsvector('english', content)) STORED
);

-- ── Indexes ───────────────────────────────────────────────────────────────────
-- IVFFlat index for cosine similarity search (768 dims, within pgvector limit)
CREATE INDEX ON chunks USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 50);

-- GIN index for fast full-text search
CREATE INDEX ON chunks USING GIN (fts_vector);

-- ── Row Level Security ───────────────────────────────────────────────────────
-- Enable RLS but allow public read access (handbook data is public)
-- Writes are blocked for anon — only service role can insert during ingestion
ALTER TABLE chunks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "allow public read"
    ON chunks FOR SELECT
    USING (true);


-- Called by the FastAPI backend via supabase.rpc("hybrid_search", {...})
-- Combines semantic (cosine, weight 0.8) + keyword (ts_rank, weight 0.2)
CREATE OR REPLACE FUNCTION hybrid_search(
    query_embedding VECTOR(768),
    query_text      TEXT,
    match_count     INT DEFAULT 6
)
RETURNS TABLE (
    id             BIGINT,
    content        TEXT,
    description    TEXT,
    heading        TEXT,
    url            TEXT,
    semantic_score FLOAT,
    keyword_score  FLOAT
)
LANGUAGE sql STABLE
AS $$
    SELECT
        id,
        content,
        description,
        heading,
        url,
        1 - (embedding <=> query_embedding)                          AS semantic_score,
        ts_rank(fts_vector, plainto_tsquery('english', query_text))  AS keyword_score
    FROM chunks
    ORDER BY
        (0.8 * (1 - (embedding <=> query_embedding)))
      + (0.2 * ts_rank(fts_vector, plainto_tsquery('english', query_text)))
    DESC
    LIMIT match_count;
$$;
