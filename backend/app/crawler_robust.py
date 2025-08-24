import asyncio
import logging
from typing import List, Set, Dict
from urllib.parse import urljoin, urlparse
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

async def crawl(start_urls: List[str], max_pages: int = 20, max_depth: int = 2, **kwargs) -> List[dict]:
    """
    A robust, Playwright-based crawler that can handle JavaScript-heavy websites.
    """
    logger.info(f"Starting Playwright crawl for: {start_urls}")
    visited: Set[str] = set()
    queue = [(url, 0) for url in start_urls]
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
            # The incorrect 'navigation_timeout' argument has been removed from here.
        )
        page = await context.new_page()

        # --- THIS IS THE CORRECT WAY TO SET THE TIMEOUT ---
        # Set the default navigation timeout for all subsequent actions on this page.
        page.set_default_navigation_timeout(30000) # 30 seconds
        # --- END OF FIX ---

        while queue and len(results) < max_pages:
            url, depth = queue.pop(0)
            
            if url in visited:
                continue
            
            visited.add(url)

            try:
                logger.info(f"Navigating to (depth {depth}, page {len(results) + 1}/{max_pages}): {url}")
                # The goto command will now use the 30-second default timeout set above.
                await page.goto(url, wait_until='domcontentloaded')
                
                # Add a small, human-like random delay
                await asyncio.sleep(1 + (0.1 * (hash(url) % 10)))

                html = await page.content()
                results.append({"url": url, "html": html})

                if depth < max_depth:
                    anchors = await page.eval_on_selector_all('a[href]', 'els => els.map(e => e.href)')
                    
                    for href in anchors:
                        if not href: continue
                        full_url = urljoin(url, href)
                        p_url = urlparse(full_url)
                        if p_url.scheme not in ('http', 'https'): continue
                        full_url_no_fragment = full_url.split('#')[0]
                        if full_url_no_fragment not in visited:
                            queue.append((full_url_no_fragment, depth + 1))

            except Exception as e:
                logger.warning(f"Playwright navigation to {url} failed. Error: {type(e).__name__}: {e}")
            
        await browser.close()
    
    logger.info(f"Playwright crawl finished. Found {len(results)} pages.")
    return results