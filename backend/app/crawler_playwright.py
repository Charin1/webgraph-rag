import asyncio
import logging
from typing import List, Dict
from urllib.parse import urljoin, urlparse
from playwright.async_api import async_playwright

from .config import settings

logger = logging.getLogger(__name__)

async def login_and_get_cookies(login_url: str, username: str, password: str,
                                username_selector: str, password_selector: str,
                                submit_selector: str, headless: bool = True):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        page = await browser.new_page()
        await page.goto(login_url)
        # fill and submit
        await page.fill(username_selector, username)
        await page.fill(password_selector, password)
        await page.click(submit_selector)
        await page.wait_for_load_state('networkidle', timeout=10000)
        cookies = await page.context.cookies()
        await browser.close()
        return cookies

async def crawl_with_playwright(start_urls: List[str], max_pages: int = None, cookies: List[Dict] = None, headless: bool = True):
    max_pages = max_pages or settings.MAX_PAGES_PER_SESSION
    visited = set()
    queue = list(start_urls)
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context()
        if cookies:
            await context.add_cookies(cookies)
        page = await context.new_page()

        while queue and len(visited) < max_pages:
            url = queue.pop(0)
            if url in visited:
                continue
            try:
                await page.goto(url, wait_until='networkidle', timeout=15000)
                html = await page.content()
                results.append({'url': url, 'html': html})
                visited.add(url)
                # extract links via DOM
                anchors = await page.eval_on_selector_all('a[href]', 'els => els.map(e => e.href)')
                for href in anchors:
                    if not href:
                        continue
                    purl = urlparse(href)
                    if purl.scheme not in ('http','https'):
                        continue
                    if href not in visited and href not in queue:
                        queue.append(href)
            except Exception as e:
                logger.warning(f'Playwright failed for {url}: {e}')
        await browser.close()
    return results
