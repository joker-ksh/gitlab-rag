# GitLab RAG Chatbot

A Retrieval-Augmented Generation chatbot for the GitLab handbook, built with:
- **Scraping**: httpx + BeautifulSoup4
- **Chunking**: Custom Python (no library)
- **LLM**: Gemini 1.5 Flash (enrichment + generation)
- **Embeddings**: Gemini text-embedding-004 (768 dims)
- **Vector DB**: Supabase (pgvector + Postgres FTS)
- **Backend**: FastAPI
- **Frontend**: React + Vite

---

## Setup

### 1. Prerequisites

- Python 3.11+
- Node.js 18+
- A [Supabase](https://supabase.com) project (free tier)
- A [Google AI Studio](https://aistudio.google.com) API key (free tier)

### 2. Environment Variables

Copy `.env` and fill in your keys:

```
GEMINI_API_KEY=your_gemini_api_key
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=your_supabase_anon_key
BACKEND_URL=http://localhost:8000
```

### 3. Supabase Schema

Run `supabase/schema.sql` in the Supabase SQL editor.
This creates the `chunks` table, both indexes, and the `hybrid_search` RPC function.

### 4. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 5. Run the Ingestion Pipeline (once)

```bash
cd ingestion
python ingest.py
```

This scrapes 11 GitLab handbook pages, chunks them, enriches each chunk with a
Gemini-generated description, embeds with text-embedding-004, and stores in Supabase.

### 6. Start the Backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```

### 7. Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

---

## Architecture

```
User query
    │
    ▼
[React Frontend]
    │  POST /chat
    ▼
[FastAPI Backend]
    ├── retrieve()          ← hybrid_search RPC (pgvector + FTS)
    ├── assess_confidence() ← guardrail on retrieval quality
    ├── generate_answer()   ← Gemini 1.5 Flash, context-only
    └── generate_related_questions() ← Gemini 1.5 Flash
    │
    ▼
[Supabase]
    ├── pgvector cosine similarity (semantic, weight 0.8)
    └── ts_rank full-text search  (keyword,  weight 0.2)
```

---

## Deployment

### Backend → Render or Railway

1. Push the repo to GitHub
2. Create a new Web Service on Render/Railway pointing to the `backend/` directory
3. Set start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Add environment variables: `GEMINI_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`, `FRONTEND_URL`

### Frontend → Vercel

1. Import the repo on Vercel, set root directory to `frontend/`
2. Add environment variable: `VITE_BACKEND_URL=https://your-backend.onrender.com`
3. Deploy

---

## Key Design Decisions

| Decision | Reason |
|---|---|
| Contextual Retrieval | Prepending LLM description to embedding_text anchors vectors to chunk meaning, not surface text |
| Hybrid search (0.8/0.2) | Semantic handles paraphrased queries; keyword catches exact GitLab-specific terms |
| Semaphore(5) on enrichment | Stays within Gemini free tier (1,500 calls/day) |
| Client-side guardrails | Avoids wasting API calls on off-topic queries |
| Confidence assessment | Prevents hallucination when retrieval quality is poor |
