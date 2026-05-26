# GitLab Handbook AI — RAG Chatbot

A production-quality Retrieval-Augmented Generation chatbot that answers questions
about the GitLab handbook. It uses hybrid semantic + keyword search backed by
pgvector and Postgres FTS, with Gemini for both contextual enrichment and answer
generation. The UI is styled to match the GitLab handbook's own design system.

---

## Architecture Overview

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                         INGESTION PIPELINE (run once)                       ║
║                                                                              ║
║  ┌─────────────┐    ┌──────────────┐    ┌───────────────┐    ┌───────────┐  ║
║  │  scraper.py │    │  chunker.py  │    │  enricher.py  │    │ ingest.py │  ║
║  │             │    │              │    │               │    │           │  ║
║  │ httpx fetch │───▶│ Split on     │───▶│ Gemini Flash  │───▶│ Embed +   │  ║
║  │ 11 handbook │    │ heading      │    │ generates     │    │ Store in  │  ║
║  │ URLs        │    │ boundaries   │    │ 30-word       │    │ Supabase  │  ║
║  │             │    │              │    │ description   │    │           │  ║
║  │ BeautifulS. │    │ 500-tok max  │    │ per chunk     │    │ 185 rows  │  ║
║  │ strips noise│    │ 50-tok overlap    │               │    │ VECTOR(768│  ║
║  └─────────────┘    └──────────────┘    └───────────────┘    └───────────┘  ║
║                                                │                             ║
║                              embedding_text =  │                             ║
║                              description +     │                             ║
║                              "\n\n" + content  │                             ║
║                              (Contextual Retrieval technique)                ║
╚══════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════╗
║                         SUPABASE DATABASE                                    ║
║                                                                              ║
║  ┌─────────────────────────────────────────────────────────────────────┐    ║
║  │  chunks table                                                        │    ║
║  │                                                                      │    ║
║  │  id │ content │ description │ heading │ url │ embedding │ fts_vector │    ║
║  │     │ (raw)   │ (30-word    │         │     │ VECTOR    │ TSVECTOR   │    ║
║  │     │         │  summary)   │         │     │ (768 dim) │ (auto)     │    ║
║  └─────────────────────────────────────────────────────────────────────┘    ║
║                                                                              ║
║  ┌──────────────────────┐    ┌──────────────────────────────────────────┐   ║
║  │ IVFFlat index        │    │ GIN index                                │   ║
║  │ on embedding         │    │ on fts_vector                            │   ║
║  │ (cosine similarity)  │    │ (full-text search)                       │   ║
║  └──────────────────────┘    └──────────────────────────────────────────┘   ║
║                                                                              ║
║  ┌─────────────────────────────────────────────────────────────────────┐    ║
║  │  hybrid_search(query_embedding, query_text, match_count)  RPC       │    ║
║  │                                                                      │    ║
║  │  score = (0.8 × cosine_similarity) + (0.2 × ts_rank)               │    ║
║  │  ORDER BY score DESC LIMIT 6                                         │    ║
║  └─────────────────────────────────────────────────────────────────────┘    ║
╚══════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════╗
║                    QUERY PIPELINE (every user message)                       ║
║                                                                              ║
║  ┌──────────────┐                                                            ║
║  │   Browser    │                                                            ║
║  │              │                                                            ║
║  │ User types   │                                                            ║
║  │ a question   │                                                            ║
║  └──────┬───────┘                                                            ║
║         │                                                                    ║
║         ▼                                                                    ║
║  ┌──────────────────────────────────────────┐                               ║
║  │  Client-side Guardrails (guardrails.js)  │                               ║
║  │                                          │                               ║
║  │  salary / compensation?  ──▶ block       │                               ║
║  │  should I quit?          ──▶ block       │                               ║
║  │  your opinion?           ──▶ block       │                               ║
║  │  anything else           ──▶ continue    │                               ║
║  └──────────────────┬───────────────────────┘                               ║
║                     │ POST /chat                                             ║
║                     ▼                                                        ║
║  ┌──────────────────────────────────────────┐                               ║
║  │         FastAPI Backend (main.py)        │                               ║
║  │                                          │                               ║
║  │  1. embed query                          │                               ║
║  │     gemini-embedding-001 → 768-dim vec   │                               ║
║  │                                          │                               ║
║  │  2. hybrid_search RPC → top 6 chunks     │                               ║
║  │     semantic score  (weight 0.8)         │                               ║
║  │     keyword score   (weight 0.2)         │                               ║
║  │     combined score  = weighted sum       │                               ║
║  │                                          │                               ║
║  │  3. assess_confidence(chunks)            │                               ║
║  │     top > 0.75 AND avg > 0.60 → high     │                               ║
║  │     top > 0.50               → medium    │                               ║
║  │     otherwise                → low/none  │                               ║
║  │                                          │                               ║
║  │  4. generate_answer(query, chunks)       │                               ║
║  │     gemini-2.5-flash                     │                               ║
║  │     context-only prompt                  │                               ║
║  │     → grounded answer string             │                               ║
║  │                                          │                               ║
║  │  5. generate_related_questions()         │                               ║
║  │     gemini-2.5-flash                     │                               ║
║  │     → ["q1", "q2", "q3"]                 │                               ║
║  └──────────────────┬───────────────────────┘                               ║
║                     │ JSON response                                          ║
║                     ▼                                                        ║
║  ┌──────────────────────────────────────────┐                               ║
║  │         React Frontend (Vite)            │                               ║
║  │                                          │                               ║
║  │  ┌─────────────────┬──────────────────┐  │                               ║
║  │  │  Chat (60%)     │ Transparency     │  │                               ║
║  │  │                 │ Panel (40%)      │  │                               ║
║  │  │ • answer text   │                  │  │                               ║
║  │  │   (markdown)    │ • query heading  │  │                               ║
║  │  │                 │ • confidence     │  │                               ║
║  │  │ • 3 follow-up   │   badge          │  │                               ║
║  │  │   question chips│ • chunk cards    │  │                               ║
║  │  │                 │   - description  │  │                               ║
║  │  │                 │   - score bars   │  │                               ║
║  │  │                 │   - source URL   │  │                               ║
║  │  └─────────────────┴──────────────────┘  │                               ║
║  └──────────────────────────────────────────┘                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

---

## Why This Architecture Works

### Contextual Retrieval
Raw chunk text alone produces poor embeddings. A chunk like *"We react to them
with values emoji"* has no semantic anchor — the vector doesn't know it's about
GitLab's CREDIT values. The fix: before embedding, call Gemini to generate a
30-word description of exactly what the chunk covers, then embed
`description + "\n\n" + content`. This anchors the vector to the chunk's precise
meaning rather than its surface words. Retrieval accuracy improves significantly.

### Hybrid Search (0.8 / 0.2)
Semantic search alone misses exact technical terms. A query for `.gitlab-ci.yml`
or `GitLab Duo` may not match well by cosine similarity if those terms weren't
in the description. Keyword search (Postgres `ts_rank`) catches exact term
matches. The 80/20 weighting keeps semantic search dominant (it handles
paraphrased queries well) while keyword search acts as a safety net.

### Confidence Assessment
Before passing chunks to the LLM, the combined scores are checked. If the top
score is below 0.50, the retrieval is poor — the LLM would hallucinate rather
than answer from context. The confidence guardrail prevents this by returning a
`low` or `none` level, which the frontend displays as a red badge and the
backend uses to skip generation entirely when confidence is `none`.

### Client-side Guardrails
Three categories of queries are blocked before any API call: compensation
questions (not in the public handbook), personal career decisions (not
answerable from a handbook), and opinion requests (the model has no opinions).
Blocking these client-side saves API quota and gives instant responses.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Scraping | Python, `httpx`, `BeautifulSoup4` |
| Chunking | Custom Python — no external library |
| LLM — enrichment + generation | `gemini-2.5-flash` via `google-generativeai==0.8.3` |
| Embedding | `gemini-embedding-001` with `output_dimensionality=768` |
| Vector + keyword DB | Supabase (pgvector + Postgres FTS) |
| Backend | FastAPI 0.115.5 + uvicorn 0.32.1 |
| Frontend | React 18 + Vite 5, Inter font, plain CSS |

---

## Prerequisites

- Python 3.13+
- Node.js 18+
- [Supabase](https://supabase.com) project (free tier)
- [Google AI Studio](https://aistudio.google.com) API key (free tier)

---

## Local Setup

### 1. Configure environment

Copy `.env.example` to `.env` and fill in all values:

```
GEMINI_API_KEY=your_gemini_api_key
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=eyJ...              # anon/public key — Project Settings → API
SUPABASE_SERVICE_KEY=eyJ...      # service_role key — ingestion only
DATABASE_URL=postgresql://postgres:PASSWORD@db.your-project-id.supabase.co:5432/postgres
BACKEND_URL=http://localhost:8000
FRONTEND_URL=http://localhost:5173
```

Set the frontend env:

```
# frontend/.env
VITE_BACKEND_URL=http://localhost:8000
```

### 2. Set up Supabase schema

In the Supabase SQL editor, run the full contents of `supabase/schema.sql`.

This creates:
- `chunks` table with `VECTOR(768)` column and auto-generated `fts_vector`
- IVFFlat index for cosine similarity (lists=50)
- GIN index for full-text search
- `hybrid_search` RPC function

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the ingestion pipeline

```bash
cd ingestion
python ingest.py
```

Runs the full pipeline once — scrape → chunk → enrich → embed → store.
Takes ~20 minutes due to free tier rate limits (10 embedding requests/minute).
Only needs to run once. Re-run only if the handbook content changes.

### 5. Start the backend

```bash
cd backend
python -m uvicorn main:app --reload --port 8000
```

Verify: `GET http://localhost:8000/health` → `{"status":"ok"}`

### 6. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**

---

## Running the Evaluation Suite

```bash
# Retrieval-only — no generation quota needed, runs immediately
python -m eval.eval_retrieval_only

# Full end-to-end — requires generation quota (20 req/day free tier)
python -m eval.evaluate
```

Reports saved to `eval/retrieval_report.json` and `eval/eval_report.json`.

---

## Key Design Decisions

| Decision | Reason |
|---|---|
| Contextual Retrieval | Prepending LLM description to `embedding_text` anchors vectors to chunk meaning |
| Hybrid search 0.8/0.2 | Semantic handles paraphrased queries; keyword catches exact GitLab-specific terms |
| `output_dimensionality=768` | Truncates `gemini-embedding-001`'s native 3072 dims to fit pgvector's index limit |
| `Semaphore(3)` on enrichment | Stays within Gemini free tier rate limits during ingestion |
| Client-side guardrails | Blocks off-topic queries before hitting the API |
| Confidence assessment | Prevents LLM hallucination when retrieval quality is poor |
| Service role key for ingest | Bypasses Supabase RLS during ingestion; anon key used for all reads |

---

## Future Enhancements

### Conversational Memory
The system is currently **stateless** — every question is treated independently.
The backend receives only the current query with no knowledge of previous turns.

This means follow-up questions like *"Can you explain the first one?"* fail
because there is no referent. A full conversational RAG system needs:

1. **Query rewriting** — before retrieval, use the conversation history to
   rewrite vague follow-ups into standalone questions:
   ```
   History:   "What are GitLab's core values?"
   Follow-up: "Can you explain the first one?"
   Rewritten: "Can you explain GitLab's Collaboration value in more detail?"
   ```

2. **History in the generation prompt** — pass the last N turns to Gemini so
   answers are contextually aware of what was already discussed.

Implementation plan when ready:
- `useChat.js` — include last 3 message pairs in the API request body
- `backend/main.py` — accept optional `history: list[dict]` in `ChatRequest`
- `backend/generation.py` — add `rewrite_query(query, history)` step before
  retrieval when history is non-empty; inject history into generation prompt
