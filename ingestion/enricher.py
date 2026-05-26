"""
Phase 2B — Contextual Enrichment via LLM (Gemini Flash)
Generates a dense 30-word description per chunk using Gemini 1.5 Flash,
then constructs embedding_text = description + "\n\n" + content.
"""

import asyncio
import json
import logging
import os
import re

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

ENRICHMENT_PROMPT = """Analyze this GitLab handbook chunk and return only valid JSON with no markdown formatting.

Tasks:
1. Write a dense one-sentence description (maximum 30 words) of exactly what \
this chunk covers. Be specific — include product names, feature names, \
process names, or GitLab-specific terminology if present. This description \
is used for search indexing, not shown to users directly.

2. Return the JSON in exactly this format:
{{
  "description": "your one sentence description here"
}}

Heading: {heading}
Content: {content}"""

MAX_CONTENT_CHARS = 600   # cap content sent to LLM
SEMAPHORE_LIMIT = 3       # max concurrent Gemini calls (free tier safe)


def _build_model() -> genai.GenerativeModel:
    return genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        generation_config=genai.types.GenerationConfig(
            max_output_tokens=80,
            temperature=0.2,
        ),
    )


def _parse_description(response_text: str, fallback: str) -> str:
    """
    Parse JSON from Gemini response.
    Strips markdown fences if present, then parses JSON.
    Falls back to `fallback` string on any error.
    """
    text = response_text.strip()

    # Strip markdown code fences if Gemini wraps the JSON anyway
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    try:
        data = json.loads(text)
        description = data.get("description", "").strip()
        if description:
            return description
        raise ValueError("Empty description field")
    except Exception as e:
        logger.warning(f"JSON parse failed for heading '{fallback}': {e} | raw='{response_text[:120]}'")
        return fallback


async def _enrich_chunk(
    chunk: dict,
    semaphore: asyncio.Semaphore,
    model: genai.GenerativeModel,
) -> dict:
    """Enrich a single chunk with an LLM-generated description."""
    heading = chunk.get("heading") or "Untitled"
    content_preview = chunk["content"][:MAX_CONTENT_CHARS]

    prompt = ENRICHMENT_PROMPT.format(heading=heading, content=content_preview)

    async with semaphore:
        description = heading  # default fallback
        for attempt in range(3):  # up to 3 retries with backoff
            try:
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None, lambda: model.generate_content(prompt)
                )
                description = _parse_description(response.text, fallback=heading)
                break
            except Exception as e:
                if "429" in str(e) and attempt < 2:
                    wait = 30 * (attempt + 1)  # 30s, 60s
                    logger.warning(f"Rate limited on enrichment, retrying in {wait}s (attempt {attempt+1})")
                    await asyncio.sleep(wait)
                else:
                    logger.error(f"Gemini call failed for heading '{heading}': {e}")
                    break

    embedding_text = f"{description}\n\n{chunk['content']}"

    return {
        **chunk,
        "description": description,
        "embedding_text": embedding_text,
    }


async def enrich_chunks(chunks: list[dict]) -> list[dict]:
    """
    Enrich all chunks concurrently (max 5 at a time) with LLM descriptions.
    Returns enriched chunk list with 'description' and 'embedding_text' fields added.
    """
    semaphore = asyncio.Semaphore(SEMAPHORE_LIMIT)
    model = _build_model()

    tasks = [_enrich_chunk(chunk, semaphore, model) for chunk in chunks]
    enriched = await asyncio.gather(*tasks)

    logger.info(f"Enrichment complete. {len(enriched)} chunks enriched.")
    return list(enriched)


if __name__ == "__main__":
    sample_chunks = [
        {
            "content": "GitLab values transparency in all decisions. Team members are encouraged to share information openly.",
            "heading": "Transparency",
            "url": "https://handbook.gitlab.com/handbook/values/",
            "chunk_index": 0,
        }
    ]
    result = asyncio.run(enrich_chunks(sample_chunks))
    for c in result:
        print(f"description: {c['description']}")
        print(f"embedding_text[:80]: {c['embedding_text'][:80]}")
