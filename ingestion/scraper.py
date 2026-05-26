"""
Phase 1 — Data Ingestion: Scraping
Scrapes high-value sections of the GitLab handbook using httpx + BeautifulSoup4.
"""

import asyncio
import logging
import httpx
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PRIORITY_URLS = [
    # Core culture and values
    "https://handbook.gitlab.com/handbook/values/",
    "https://handbook.gitlab.com/handbook/communication/",
    "https://handbook.gitlab.com/handbook/company/culture/all-remote/",
    # People and hiring
    "https://handbook.gitlab.com/handbook/people-group/",
    "https://handbook.gitlab.com/handbook/hiring/",
    "https://handbook.gitlab.com/handbook/leadership/",
    # Product and engineering
    "https://handbook.gitlab.com/handbook/engineering/",
    "https://handbook.gitlab.com/handbook/product/",
    "https://handbook.gitlab.com/handbook/security/",
    "https://handbook.gitlab.com/handbook/marketing/",
    # Direction and strategy
    "https://handbook.gitlab.com/handbook/about/direction",
]

TIMEOUT = 10  # seconds per request


async def scrape_page(client: httpx.AsyncClient, url: str, visited: set) -> dict | None:
    """Scrape a single page and return a page dict, or None on failure/duplicate."""
    if url in visited:
        logger.info(f"Skipping already visited URL: {url}")
        return None

    visited.add(url)

    try:
        response = await client.get(url, timeout=TIMEOUT)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to fetch {url}: {e}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")

    # Extract title
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else url

    # Extract main content container: <main> → <article> → <body>
    container = soup.find("main") or soup.find("article") or soup.find("body")
    if not container:
        logger.warning(f"No content container found for {url}")
        return None

    # Remove noise tags in-place
    for tag in container.find_all(["nav", "footer", "script", "style"]):
        tag.decompose()

    # Extract headings
    headings = [h.get_text(strip=True) for h in container.find_all(["h1", "h2", "h3"])]

    # Extract clean body text
    content = container.get_text(separator="\n", strip=True)

    logger.info(f"Scraped: {url} | title='{title}' | headings={len(headings)} | chars={len(content)}")

    return {
        "url": url,
        "title": title,
        "content": content,
        "headings": headings,
    }


async def scrape_priority_sections() -> list[dict]:
    """Scrape all priority URLs and return a list of page dicts."""
    visited: set = set()
    pages = []

    async with httpx.AsyncClient(follow_redirects=True) as client:
        tasks = [scrape_page(client, url, visited) for url in PRIORITY_URLS]
        results = await asyncio.gather(*tasks)

    for result in results:
        if result is not None:
            pages.append(result)

    logger.info(f"Scraping complete. {len(pages)}/{len(PRIORITY_URLS)} pages retrieved.")
    return pages


if __name__ == "__main__":
    pages = asyncio.run(scrape_priority_sections())
    for p in pages:
        print(f"  {p['url']} — {len(p['content'])} chars, {len(p['headings'])} headings")
