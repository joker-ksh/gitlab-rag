"""
Phase 2A — Structural Chunking
Splits scraped pages into meaningful chunks by heading hierarchy.
No external chunking library — pure Python logic.
"""

import re
import logging

logger = logging.getLogger(__name__)

# Token approximation constants
WORDS_PER_TOKEN = 0.75          # 1 token ≈ 0.75 words  →  1 word ≈ 1.33 tokens
MAX_TOKENS = 500                # max tokens per chunk
OVERLAP_TOKENS = 50             # overlap between sliding windows
MIN_TOKENS = 50                 # discard chunks below this size

MAX_WORDS = int(MAX_TOKENS * WORDS_PER_TOKEN)       # ~375 words
OVERLAP_WORDS = int(OVERLAP_TOKENS * WORDS_PER_TOKEN)  # ~38 words
MIN_WORDS = int(MIN_TOKENS * WORDS_PER_TOKEN)       # ~38 words


def word_count(text: str) -> int:
    return len(text.split())


def approx_tokens(text: str) -> int:
    """Approximate token count from word count."""
    return int(word_count(text) / WORDS_PER_TOKEN)


def sliding_window_split(text: str, heading: str, url: str, base_index: int) -> list[dict]:
    """
    Split an oversized section into overlapping windows of MAX_WORDS words
    with OVERLAP_WORDS overlap. Returns a list of chunk dicts.
    """
    words = text.split()
    chunks = []
    start = 0
    window_num = 0

    while start < len(words):
        end = start + MAX_WORDS
        window_words = words[start:end]
        window_text = " ".join(window_words)

        if word_count(window_text) >= MIN_WORDS:
            chunks.append({
                "content": window_text,
                "heading": heading,
                "url": url,
                "chunk_index": base_index + window_num,
            })
            window_num += 1

        if end >= len(words):
            break

        # Advance by (MAX_WORDS - OVERLAP_WORDS) to create overlap
        start += MAX_WORDS - OVERLAP_WORDS

    return chunks


def chunk_page(page: dict) -> list[dict]:
    """
    Chunk a single page dict into a list of chunk dicts.
    Splits on heading boundaries first, then applies sliding window for oversized sections.
    """
    content = page["content"]
    url = page["url"]
    chunks = []
    chunk_index = 0

    # Split on heading boundaries: lines starting with # / ## / ###
    # The regex keeps the heading line at the start of each section
    sections = re.split(r'\n(?=#{1,3} )', content)

    for section in sections:
        if not section.strip():
            continue

        lines = section.split("\n", 1)
        first_line = lines[0].strip()

        # Extract heading — strip leading # characters
        if re.match(r'^#{1,3} ', first_line):
            heading = re.sub(r'^#{1,3} ', '', first_line).strip()
            body = lines[1].strip() if len(lines) > 1 else ""
        else:
            # No heading marker — treat the whole section as body with empty heading
            heading = ""
            body = section.strip()

        if not body:
            continue

        body_words = word_count(body)

        if body_words < MIN_WORDS:
            # Too short — discard
            logger.debug(f"Discarding short chunk under heading '{heading}' ({body_words} words)")
            continue

        if body_words <= MAX_WORDS:
            # Fits within limit — keep as single chunk
            chunks.append({
                "content": body,
                "heading": heading,
                "url": url,
                "chunk_index": chunk_index,
            })
            chunk_index += 1
        else:
            # Oversized — apply sliding window
            windows = sliding_window_split(body, heading, url, chunk_index)
            chunks.extend(windows)
            chunk_index += len(windows)

    return chunks


def chunk_by_headings(pages: list[dict]) -> list[dict]:
    """Chunk all pages and return a flat list of chunk dicts."""
    all_chunks = []
    for page in pages:
        page_chunks = chunk_page(page)
        all_chunks.extend(page_chunks)
        logger.info(f"Chunked {page['url']} → {len(page_chunks)} chunks")

    logger.info(f"Total chunks produced: {len(all_chunks)}")
    return all_chunks


if __name__ == "__main__":
    # Quick smoke test with synthetic data
    sample_page = {
        "url": "https://handbook.gitlab.com/handbook/values/",
        "title": "GitLab Values",
        "content": (
            "# Collaboration\n"
            "GitLab values collaboration above all else. " * 20 + "\n"
            "## Transparency\n"
            "We are transparent in everything we do. " * 5 + "\n"
            "### Short\n"
            "Too short."
        ),
        "headings": ["Collaboration", "Transparency", "Short"],
    }
    result = chunk_by_headings([sample_page])
    for c in result:
        print(f"  [{c['chunk_index']}] heading='{c['heading']}' words={word_count(c['content'])}")
