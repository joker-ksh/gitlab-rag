"""
Phase 4 — Hybrid Retrieval
Combines semantic (pgvector cosine) + keyword (Postgres FTS ts_rank) search.
Fixed weights: semantic=0.8, keyword=0.2

Two retrieval paths:
  1. PRIMARY  — Supabase RPC `hybrid_search` (uses REST API via supabase-py)
  2. FALLBACK — Direct asyncpg connection using DATABASE_URL (raw SQL)
"""

import logging
import os

import google.generativeai as genai
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
logger = logging.getLogger(__name__)

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

EMBEDDING_MODEL = "models/gemini-embedding-001"
EMBEDDING_DIM = 768

_supabase_client: Client | None = None


def get_supabase() -> Client:
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = create_client(
            os.environ["SUPABASE_URL"],
            os.environ["SUPABASE_KEY"],
        )
    return _supabase_client


def embed_query(query: str) -> list[float]:
    """Embed a query string using gemini-embedding-001 (768 dims)."""
    result = genai.embed_content(
        model=EMBEDDING_MODEL,
        content=query,
        task_type="retrieval_query",
        output_dimensionality=768,
    )
    vector = result["embedding"]
    assert len(vector) == EMBEDDING_DIM, f"Expected {EMBEDDING_DIM} dims, got {len(vector)}"
    return vector


async def _retrieve_via_rpc(
    query_embedding: list[float],
    query: str,
    top_k: int,
) -> list[dict] | None:
    """
    Primary path: call the hybrid_search Postgres function via Supabase REST API.
    Returns list of row dicts, or None if the RPC call fails.
    """
    supabase = get_supabase()
    try:
        response = supabase.rpc(
            "hybrid_search",
            {
                "query_embedding": query_embedding,
                "query_text": query,
                "match_count": top_k,
            },
        ).execute()
        return response.data or []
    except Exception as e:
        logger.warning(f"Supabase RPC hybrid_search failed, will try asyncpg fallback: {e}")
        return None


async def _retrieve_via_asyncpg(
    query_embedding: list[float],
    query: str,
    top_k: int,
) -> list[dict]:
    """
    Fallback path: run the hybrid search SQL directly via asyncpg.
    Requires DATABASE_URL in environment.
    """
    import asyncpg

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL not set — cannot use asyncpg fallback.")
        return []

    # asyncpg needs the postgresql:// scheme (not postgres://)
    database_url = database_url.replace("postgres://", "postgresql://", 1)

    sql = """
        SELECT
            id,
            content,
            description,
            heading,
            url,
            1 - (embedding <=> $1::vector)                          AS semantic_score,
            ts_rank(fts_vector, plainto_tsquery('english', $2))     AS keyword_score
        FROM chunks
        ORDER BY
            (0.8 * (1 - (embedding <=> $1::vector)))
          + (0.2 * ts_rank(fts_vector, plainto_tsquery('english', $2)))
        DESC
        LIMIT $3
    """

    try:
        conn = await asyncpg.connect(database_url)
        try:
            # Pass embedding as a formatted vector string
            embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
            rows = await conn.fetch(sql, embedding_str, query, top_k)
            return [dict(row) for row in rows]
        finally:
            await conn.close()
    except Exception as e:
        logger.error(f"asyncpg fallback also failed: {e}")
        return []


async def retrieve(query: str, top_k: int = 6) -> list[dict]:
    """
    Hybrid retrieval: semantic (0.8) + keyword (0.2) combined score.
    Returns top_k chunks sorted by combined_score descending.
    """
    # 1. Embed the query
    query_embedding = embed_query(query)

    # 2. Try primary path (Supabase RPC), fall back to asyncpg
    rows = await _retrieve_via_rpc(query_embedding, query, top_k)
    if rows is None:
        rows = await _retrieve_via_asyncpg(query_embedding, query, top_k)

    # 3. Compute combined score and normalise field names
    results = []
    for row in rows:
        semantic_score = float(row.get("semantic_score", 0.0))
        keyword_score = float(row.get("keyword_score", 0.0))
        combined_score = round(0.8 * semantic_score + 0.2 * keyword_score, 4)
        results.append(
            {
                "id": row.get("id"),
                "content": row.get("content", ""),
                "description": row.get("description", ""),
                "heading": row.get("heading", ""),
                "url": row.get("url", ""),
                "semantic_score": round(semantic_score, 4),
                "keyword_score": round(keyword_score, 4),
                "combined_score": combined_score,
            }
        )

    # Sort by combined_score descending (RPC already does this, but be safe)
    results.sort(key=lambda x: x["combined_score"], reverse=True)
    return results[:top_k]


def assess_confidence(chunks: list[dict]) -> dict:
    """
    Assess retrieval quality to prevent hallucination on poor results.
    Returns a confidence dict with 'level' and 'message'.
    """
    if not chunks:
        return {
            "level": "none",
            "message": "No relevant content found in the GitLab handbook for this query.",
        }

    top_score = chunks[0]["combined_score"]
    avg_score = sum(c["combined_score"] for c in chunks) / len(chunks)

    if top_score > 0.75 and avg_score > 0.60:
        return {"level": "high", "message": None}
    elif top_score > 0.50:
        return {
            "level": "medium",
            "message": "Answer based on partially relevant content. Verify with the source links below.",
        }
    else:
        return {
            "level": "low",
            "message": "Could not find strong matches in the handbook. This topic may not be covered.",
        }
