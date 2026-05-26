"""
Phase 5 — Answer Generation
Uses Gemini 1.5 Flash to generate grounded answers from retrieved chunks,
then generates 3 related follow-up questions.
"""

import json
import logging
import os
import re

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

GENERATION_PROMPT = """You are a helpful assistant for GitLab employees and aspiring employees.
Answer the question using ONLY the context provided below.
Do not use any knowledge outside the provided context.
If the answer is not present in the context, say exactly:
"I could not find information about this in the GitLab handbook."

Context:
{context}

Question: {query}

Answer:"""

RELATED_QUESTIONS_PROMPT = """Given this question about the GitLab handbook: "{query}"
And this answer: "{answer}"

Generate exactly 3 short follow-up questions a GitLab employee \
would naturally want to ask next. Be specific to GitLab context.
Return only a valid JSON array of 3 strings, no other text.

Example format: ["question 1", "question 2", "question 3"]"""


def _get_model() -> genai.GenerativeModel:
    return genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        generation_config=genai.types.GenerationConfig(
            temperature=0.3,
        ),
    )


async def generate_answer(query: str, chunks: list[dict]) -> str:
    """
    Generate a grounded answer from retrieved chunks.
    Uses raw 'content' field — never 'description'.
    """
    context = "\n\n---\n\n".join(
        f"Source: {c['url']}\nSection: {c['heading']}\n{c['content']}"
        for c in chunks
    )

    prompt = GENERATION_PROMPT.format(context=context, query=query)

    import asyncio
    model = _get_model()
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None, lambda: model.generate_content(prompt)
    )
    return response.text.strip()


async def generate_related_questions(query: str, answer: str) -> list[str]:
    """
    Generate 3 follow-up questions based on the query and answer.
    Returns a list of 3 strings, or [] on any failure.
    """
    prompt = RELATED_QUESTIONS_PROMPT.format(query=query, answer=answer[:800])

    import asyncio
    model = _get_model()
    loop = asyncio.get_event_loop()

    try:
        response = await loop.run_in_executor(
            None, lambda: model.generate_content(prompt)
        )
        raw = response.text.strip()

        # Strip markdown fences if present
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        questions = json.loads(raw)
        if isinstance(questions, list) and len(questions) >= 3:
            return [str(q) for q in questions[:3]]
        return []
    except Exception as e:
        logger.warning(f"Related questions generation failed: {e}")
        return []
