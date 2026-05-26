"""
Phase 6 — FastAPI Backend
Exposes POST /chat and GET /health endpoints.
"""

import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from retrieval import retrieve, assess_confidence
from generation import generate_answer, generate_related_questions

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="GitLab RAG Chatbot", version="1.0.0")

# ── CORS ──────────────────────────────────────────────────────────────────────
# Allow localhost:5173 (Vite dev) and any Vercel deployment URL.
# In production, replace "*" with your exact Vercel URL.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        os.environ.get("FRONTEND_URL", "*"),
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ─────────────────────────────────────────────────
class ChatRequest(BaseModel):
    query: str


class ConfidenceModel(BaseModel):
    level: str
    message: str | None


class ChunkModel(BaseModel):
    description: str
    heading: str
    url: str
    semantic_score: float
    keyword_score: float
    combined_score: float


class ChatResponse(BaseModel):
    answer: str
    confidence: ConfidenceModel
    related_questions: list[str]
    chunks: list[ChunkModel]


# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    """Health check — used to verify deployment."""
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint.
    1. Retrieve relevant chunks (hybrid semantic + keyword search)
    2. Assess confidence
    3. Generate answer from chunks
    4. Generate related follow-up questions
    """
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query must not be empty.")

    try:
        # Step 1 — Retrieve
        chunks = await retrieve(query, top_k=6)

        # Step 2 — Confidence
        confidence = assess_confidence(chunks)

        # Step 3 — Generate answer
        if confidence["level"] == "none":
            answer = "No relevant content found in the GitLab handbook for this query."
            related_questions: list[str] = []
        else:
            answer = await generate_answer(query, chunks)
            # Step 4 — Related questions
            related_questions = await generate_related_questions(query, answer)

        # Build response chunks (strip raw content — not sent to frontend)
        response_chunks = [
            ChunkModel(
                description=c.get("description", ""),
                heading=c.get("heading", ""),
                url=c.get("url", ""),
                semantic_score=c.get("semantic_score", 0.0),
                keyword_score=c.get("keyword_score", 0.0),
                combined_score=c.get("combined_score", 0.0),
            )
            for c in chunks
        ]

        return ChatResponse(
            answer=answer,
            confidence=ConfidenceModel(**confidence),
            related_questions=related_questions,
            chunks=response_chunks,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unhandled error in /chat: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
