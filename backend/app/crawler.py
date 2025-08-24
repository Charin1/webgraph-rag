import asyncio
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import List, Set
import logging
from .config import settings

logger = logging.getLogger(__name__)

async def fetch_page(client: httpx.AsyncClient, url: str, timeout=15):
    try:
        r = await client.get(url, timeout=timeout)
        r.raise_for_status()
        return r.text
    except Exception as e:
        logger.warning(f"Failed to fetch {url}: {e}")
        return None

async def crawl(start_urls: List[str], max_pages: int = None) -> List[dict]:
    max_pages = max_pages or settings.MAX_PAGES_PER_SESSION
    visited: Set[str] = set()
    queue = list(start_urls)
    results = []

    async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
        while queue and len(visited) < max_pages:
            url = queue.pop(0)
            if url in visited:
                continue
            html = await fetch_page(client, url)
            visited.add(url)
            if not html:
                continue
            results.append({"url": url, "html": html})

            soup = BeautifulSoup(html, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                href = urljoin(url, href)
                p = urlparse(href)
                if p.scheme not in ("http", "https"):
                    continue
                if href not in visited and href not in queue:
                    queue.append(href)
            await asyncio.sleep(0.01)

    return results
