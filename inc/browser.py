from __future__ import annotations
import asyncio
from playwright.async_api import async_playwright, BrowserType, BrowserContext, Browser, Page, Playwright
from loguru import logger
import time

class BrowserManager:
    browser: Browser
    context: BrowserContext
    __playwright: Playwright

    @classmethod
    async def create(cls) -> BrowserManager:
        try:
            self = cls()
            self.__playwright = await async_playwright().start()
            browser_type: BrowserType = self.__playwright.chromium
            logger.trace("Launching browser")
            self.browser = await browser_type.launch(headless=False)
            logger.trace("Browser launched")
            self.context = await self.browser.new_context()
            return self
        except Exception as e:
            logger.error(f"Failed to launch browser: {e}")
            raise e

    async def open_page(self, url: str) -> Page:
        logger.trace("call self.context.new_page()")
        page = await self.context.new_page();
        logger.trace("call goto: {}", url)
        await page.goto(url, timeout=25 * 1000, wait_until="load")
        logger.trace("goto: {} done", url)
        return page

    async def wait_for(self, page: Page, selector: str, timeout: int = 10000, interval: int = 200):
        logger.trace("Waiting for {selector}")
        exec_start_time = time.time()
        while time.time() <= exec_start_time + timeout / 1000: 
            cnt = await page.locator(selector).count()
            if cnt > 0:
                return
            await asyncio.sleep(float(interval) / 1000)
        raise Exception(f"Selector {selector} not found. Waiting time {timeout} exceeded")
